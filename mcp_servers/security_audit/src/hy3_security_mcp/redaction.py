"""Deterministic credential redaction — no LLM involved.

``CREDENTIAL_PATTERNS`` is the shared regex base: Task 4 (this module) uses it
to scrub secrets out of diff text before it ever reaches a prompt, and Task
5's local secret scanner reuses the exact same patterns as its detector base.
Keeping the tuple importable and named (rather than inlining regexes in both
places) is what makes that reuse possible.
"""

from __future__ import annotations

import re

# PRIVATE_KEY is FIRST on purpose: a PEM block is the widest, highest-confidence
# credential span, and redact()'s overlap resolution gives earlier patterns
# priority. Listing it first means the whole BEGIN…END block is claimed before
# any coincidental inner match (e.g. an AWS-key-shaped run in the base64 body),
# so the block stays atomic — one marker — instead of being carved into pieces.
# The body is matched non-greedily ([\s\S]*?) so two adjacent key blocks never
# merge into a single span that swallows the text between them.
CREDENTIAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "PRIVATE_KEY",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
            r"[\s\S]*?"
            r"-----END [A-Z0-9 ]*PRIVATE KEY-----"
        ),
    ),
    ("OPENAI_KEY", re.compile(r"sk-[A-Za-z0-9_-]{16,}")),
    ("AWS_ACCESS_KEY", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GITHUB_TOKEN", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("SLACK_TOKEN", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    (
        "GENERIC_SECRET",
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    ),
)


def redact(text: str) -> str:
    """Replace every credential-pattern match with ``***REDACTED-<NAME>***``.

    Only matched spans are replaced, so code surrounding a match (variable
    names, quotes, unrelated lines) is left intact. Purely regex-based —
    deterministic, no LLM call.

    Matches are collected from the ORIGINAL text across all patterns in one
    pass, not by chaining ``pattern.sub`` calls: a chained approach would let
    a later, broader pattern (e.g. GENERIC_SECRET's ``label = "value"``) match
    across an earlier pattern's already-inserted ``***REDACTED-...***``
    placeholder, clobbering it.

    Overlapping spans are resolved by CREDENTIAL_PATTERNS priority: a
    higher-priority match (earlier in the tuple, e.g. OPENAI_KEY) is placed
    first, and a lower-priority match (e.g. GENERIC_SECRET) that overlaps it
    is *trimmed* to its non-overlapping sub-ranges rather than dropped whole —
    each surviving sub-range is still redacted. Dropping the loser entirely
    would leak the bytes of the broad span that fall outside the narrow one
    (e.g. the tail of a password value that merely contains an AWS key). Every
    byte of every matched span is therefore masked. The placeholder text
    contains no ``= "..."`` shape, so redact() is idempotent — a second pass
    finds no matches in the output.
    """
    candidates: list[tuple[int, int, int, str]] = sorted(
        (priority, match.start(), match.end(), name)
        for priority, (name, pattern) in enumerate(CREDENTIAL_PATTERNS)
        for match in pattern.finditer(text)
    )

    # Process highest-priority (lowest index) first; trim each candidate to the
    # parts of its span not already claimed by an accepted span.
    accepted: list[tuple[int, int, str]] = []
    for _priority, start, end, name in candidates:
        for sub_start, sub_end in _subtract(start, end, accepted):
            accepted.append((sub_start, sub_end, name))

    accepted.sort(key=lambda span: span[0])
    pieces: list[str] = []
    cursor = 0
    for start, end, name in accepted:
        pieces.append(text[cursor:start])
        pieces.append(f"***REDACTED-{name}***")
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


def _subtract(start: int, end: int, claimed: list[tuple[int, int, str]]) -> list[tuple[int, int]]:
    """Return the sub-ranges of [start, end) not covered by any claimed span.

    ``claimed`` spans are pairwise non-overlapping (only non-overlapping
    sub-ranges are ever appended), so subtracting them is a simple left-to-right
    sweep over the ones that intersect [start, end).
    """
    covering = sorted(
        (c_start, c_end) for c_start, c_end, _ in claimed if c_start < end and c_end > start
    )
    free: list[tuple[int, int]] = []
    cursor = start
    for c_start, c_end in covering:
        if c_start > cursor:
            free.append((cursor, min(c_start, end)))
        cursor = max(cursor, c_end)
        if cursor >= end:
            break
    if cursor < end:
        free.append((cursor, end))
    return free
