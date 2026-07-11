"""Local, pure-regex + Shannon-entropy secret detector — no LLM involved.

``scan_text`` is the entrypoint: a regex pass over CREDENTIAL_PATTERNS (Task
4's shared regex base, reused here rather than re-declared) followed by an
entropy pass over long tokens not already covered by a regex hit on their
line. Both passes are deterministic and local; the resulting
``SecretCandidate`` list is what Task 5's ``triage_secrets`` hands to Hy3 —
the raw secret bytes themselves must NEVER survive into a candidate's
snippet, whether or not the candidate came from a known credential shape.
"""

from __future__ import annotations

import bisect
import math
import re
from collections import Counter

import pydantic

from hy3_security_mcp.redaction import CREDENTIAL_PATTERNS, _subtract, redact

# Tokenization boundary for the entropy pass: base64/URL-safe-ish charset.
# Assignment/separator chars ('=' and ':') are DELIBERATELY excluded so a
# tight, unquoted `LABEL=secret` / `KEY:secret` (env-var / Dockerfile ENV /
# shell export / YAML shape — which GENERIC_SECRET's quote-requiring regex
# does not catch) tokenizes label and value independently: the value gets its
# own entropy check instead of a long, low-diversity label diluting the merged
# token below threshold and hiding the secret. ':' was never in the charset;
# '=' is dropped here — for base64 it only ever appears as trailing padding
# (no entropy), so the body's entropy is essentially unchanged and still above
# threshold once the padding is split off.
_TOKEN_RE = re.compile(r"[A-Za-z0-9+/_-]+")

_ENTROPY_MASK = "***REDACTED-HIGH_ENTROPY***"


class SecretCandidate(pydantic.BaseModel):
    """One candidate secret surfaced by the local scanner (unverified — Hy3
    triages true positive vs false positive downstream)."""

    kind: str
    line: int
    column: int
    snippet: str
    entropy: float | None = None


def shannon_entropy(token: str) -> float:
    """Shannon entropy of `token` in bits/char. Empty string -> 0.0."""
    if not token:
        return 0.0
    length = len(token)
    counts = Counter(token)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def _line_starts(text: str) -> list[int]:
    """0-based char offset where each line (by 1-based index) starts."""
    starts = [0]
    for i, char in enumerate(text):
        if char == "\n":
            starts.append(i + 1)
    return starts


def _locate(offset: int, starts: list[int]) -> tuple[int, int]:
    """Return (1-based line, 1-based column) for a char offset into text."""
    line = bisect.bisect_right(starts, offset)
    column = offset - starts[line - 1] + 1
    return line, column


def _qualifying_entropy_tokens(
    text: str, *, min_entropy: float, min_token_len: int
) -> list[tuple[int, int, float]]:
    """Return (start, end, entropy) for every token in `text` at least
    `min_token_len` chars long whose Shannon entropy is at least
    `min_entropy` bits/char."""
    return [
        (token_match.start(), token_match.end(), entropy)
        for token_match in _TOKEN_RE.finditer(text)
        if len(token_match.group()) >= min_token_len
        and (entropy := shannon_entropy(token_match.group())) >= min_entropy
    ]


def _mask_spans(text: str, spans: list[tuple[int, int]]) -> str:
    """Replace each (start, end) span in `text` with `_ENTROPY_MASK`,
    processing right-to-left so earlier offsets stay valid as later ones are
    substituted."""
    masked = text
    for start, end in sorted(spans, reverse=True):
        masked = masked[:start] + _ENTROPY_MASK + masked[end:]
    return masked


def scan_text(
    text: str, *, min_entropy: float = 4.0, min_token_len: int = 20
) -> list[SecretCandidate]:
    """Scan `text` for candidate secrets: a regex pass, then an entropy pass.

    Deterministic and purely local — no LLM call. The regex pass uses
    CREDENTIAL_PATTERNS (redaction.py's shared base); each match becomes one
    candidate keyed by (line, pattern name), deduped so repeated matches of
    the same kind on the same line collapse to a single row. The entropy pass
    tokenizes each line on non-``[A-Za-z0-9+/_=-]`` boundaries and flags
    tokens at least `min_token_len` chars long whose Shannon entropy is at
    least `min_entropy` bits/char — but only on lines not already covered by
    a regex match, and at most one ``high_entropy`` candidate per line.

    This is intentionally high-recall: base64 blobs, git SHAs (at a lowered
    threshold), UUIDs and the like can and do surface as `high_entropy`
    candidates. That is by design — Hy3's triage step is what tells true
    positives from false positives; the scanner's job is not to miss things.

    Every snippet is masked so the raw secret is never emitted, whether or not
    the candidate came from a known credential shape:

    - high_entropy candidates: redact() alone cannot mask these — it only
      knows CREDENTIAL_PATTERNS — so every qualifying token's exact span is
      masked directly before redact() is layered on for defense-in-depth
      against any other pattern on the line.
    - regex candidates: a line can ALSO carry a second, entropy-only secret
      co-located with the known-shape credential (e.g. an inline AWS access-
      key-id + secret pair) — a shape no CREDENTIAL_PATTERNS entry matches.
      Marking the line regex-covered means the entropy pass above never runs
      on it, so the regex candidate's own span is independently scanned for
      qualifying high-entropy tokens OUTSIDE the credential match itself and
      those are masked too, before redact() is layered on.
    """
    lines = text.splitlines()
    starts = _line_starts(text)

    candidates: dict[tuple[int, str], SecretCandidate] = {}
    regex_covered_lines: set[int] = set()

    for name, pattern in CREDENTIAL_PATTERNS:
        for match in pattern.finditer(text):
            start_line, column = _locate(match.start(), starts)
            end_line, _ = _locate(max(match.end() - 1, match.start()), starts)
            regex_covered_lines.update(range(start_line, end_line + 1))

            key = (start_line, name)
            if key in candidates:
                continue
            span_text = "\n".join(lines[start_line - 1 : end_line])

            # Any other high-entropy secret co-located in this span (but
            # outside the credential shapes redact() will mask) must be masked
            # here too, or it survives raw into the snippet. A qualifying
            # entropy token can PARTIALLY overlap a credential span — e.g.
            # `AKIA…/secret` tokenizes as one run because '/' is in the entropy
            # charset — so we must not drop the whole token (that leaks its
            # non-overlapping tail); instead subtract the credential spans and
            # mask only the sub-ranges outside them, reusing redaction.py's
            # interval-subtract helper.
            credential_spans = [
                (cred_match.start(), cred_match.end(), name)
                for name, cred_pattern in CREDENTIAL_PATTERNS
                for cred_match in cred_pattern.finditer(span_text)
            ]
            entropy_spans = [
                sub
                for start, end, _ in _qualifying_entropy_tokens(
                    span_text, min_entropy=min_entropy, min_token_len=min_token_len
                )
                for sub in _subtract(start, end, credential_spans)
            ]
            masked_span = _mask_spans(span_text, entropy_spans)

            candidates[key] = SecretCandidate(
                kind=name, line=start_line, column=column, snippet=redact(masked_span)
            )

    for line_no, line_text in enumerate(lines, start=1):
        if line_no in regex_covered_lines:
            continue

        qualifying = _qualifying_entropy_tokens(
            line_text, min_entropy=min_entropy, min_token_len=min_token_len
        )
        if not qualifying:
            continue

        # Mask every qualifying token (not just the reported one) so no raw
        # high-entropy token can leak via a second occurrence on the line,
        # even though only the first becomes the one reported candidate.
        masked = _mask_spans(line_text, [(start, end) for start, end, _ in qualifying])

        first_start, _, first_entropy = min(qualifying, key=lambda q: q[0])
        candidates[(line_no, "high_entropy")] = SecretCandidate(
            kind="high_entropy",
            line=line_no,
            column=first_start + 1,
            snippet=redact(masked),
            entropy=first_entropy,
        )

    return sorted(candidates.values(), key=lambda c: (c.line, c.column))
