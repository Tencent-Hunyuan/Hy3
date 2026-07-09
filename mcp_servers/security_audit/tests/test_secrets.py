"""Tests for the local secret scanner: regex + entropy candidate detection.

Pure-local, deterministic, no LLM involved. The regex pass reuses
CREDENTIAL_PATTERNS from redaction.py (Task 4) as its detector base; the
entropy pass is a second, independent detector over long non-pattern-shaped
tokens. Every candidate's snippet must NEVER contain the raw secret bytes —
that is the property this whole file is built to prove, for both detectors.
"""

from __future__ import annotations

import math

from hy3_security_mcp.redaction import CREDENTIAL_PATTERNS
from hy3_security_mcp.secrets import scan_text, shannon_entropy


class TestShannonEntropy:
    def test_empty_string_is_zero(self) -> None:
        assert shannon_entropy("") == 0.0

    def test_all_same_char_is_zero(self) -> None:
        assert shannon_entropy("aaaaaaaaaaaaaaaaaaaa") == 0.0

    def test_uniform_alphabet_matches_log2_of_symbol_count(self) -> None:
        # Every one of the 62 symbols appears exactly once: the theoretical
        # maximum entropy for this alphabet size.
        token = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        assert math.isclose(shannon_entropy(token), math.log2(len(set(token))))

    def test_two_symbol_alternation_is_exactly_one_bit(self) -> None:
        assert shannon_entropy("ababababab") == 1.0


class TestRegexPassPerPatternKind:
    """One planted, realistic token per CREDENTIAL_PATTERNS kind: correct
    kind, correct 1-based line/column, and the raw token absent from the
    snippet (redact()-masked)."""

    def test_openai_key_candidate(self) -> None:
        secret = "sk-abcdefghijklmnopqrstuvwx1234"
        text = f'line0\nOPENAI_API_KEY = "{secret}"\nline2\n'

        matches = [c for c in scan_text(text) if c.kind == "OPENAI_KEY"]

        assert len(matches) == 1
        candidate = matches[0]
        assert candidate.line == 2
        assert candidate.column == text.splitlines()[1].index(secret) + 1
        assert secret not in candidate.snippet
        assert "***REDACTED-OPENAI_KEY***" in candidate.snippet

    def test_aws_access_key_candidate(self) -> None:
        secret = "AKIAIOSFODNN7EXAMPLE"
        text = f'line0\naws_key = "{secret}"\nline2\n'

        matches = [c for c in scan_text(text) if c.kind == "AWS_ACCESS_KEY"]

        assert len(matches) == 1
        candidate = matches[0]
        assert candidate.line == 2
        assert candidate.column == text.splitlines()[1].index(secret) + 1
        assert secret not in candidate.snippet
        assert "***REDACTED-AWS_ACCESS_KEY***" in candidate.snippet

    def test_github_token_candidate(self) -> None:
        secret = "ghp_abcdefghijklmnopqrstuvwxyz1234"
        text = f"line0\nGITHUB_TOKEN={secret}\nline2\n"

        matches = [c for c in scan_text(text) if c.kind == "GITHUB_TOKEN"]

        assert len(matches) == 1
        candidate = matches[0]
        assert candidate.line == 2
        assert candidate.column == text.splitlines()[1].index(secret) + 1
        assert secret not in candidate.snippet
        assert "***REDACTED-GITHUB_TOKEN***" in candidate.snippet

    def test_slack_token_candidate(self) -> None:
        secret = "xoxb-1234567890-abcdefghij"
        text = f"line0\nSLACK_TOKEN={secret}\nline2\n"

        matches = [c for c in scan_text(text) if c.kind == "SLACK_TOKEN"]

        assert len(matches) == 1
        candidate = matches[0]
        assert candidate.line == 2
        assert candidate.column == text.splitlines()[1].index(secret) + 1
        assert secret not in candidate.snippet
        assert "***REDACTED-SLACK_TOKEN***" in candidate.snippet

    def test_generic_secret_candidate(self) -> None:
        secret = "hunter2trustno1"
        text = f'line0\npassword = "{secret}"\nline2\n'

        matches = [c for c in scan_text(text) if c.kind == "GENERIC_SECRET"]

        assert len(matches) == 1
        candidate = matches[0]
        assert candidate.line == 2
        # GENERIC_SECRET matches the whole `label = "value"` construct, so
        # the match (and its column) starts at the label, not the value.
        assert candidate.column == text.splitlines()[1].index("password") + 1
        assert secret not in candidate.snippet
        assert "***REDACTED-GENERIC_SECRET***" in candidate.snippet

    def test_private_key_candidate_spans_multiple_lines(self) -> None:
        body = (
            "MIIEpAIBAAKCAQEA1234567890abcdefGHIJKLMNOPqrstuvwxyzABCDEFGHIJKLMNOP"
            "QRSTUVWXYZ0123456789"
        )
        text = (
            "before\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            f"{body}\n"
            "-----END RSA PRIVATE KEY-----\n"
            "after\n"
        )

        matches = [c for c in scan_text(text) if c.kind == "PRIVATE_KEY"]

        assert len(matches) == 1
        candidate = matches[0]
        assert candidate.line == 2  # the BEGIN line
        assert candidate.column == 1
        assert body not in candidate.snippet
        assert "-----BEGIN RSA PRIVATE KEY-----" not in candidate.snippet
        assert "***REDACTED-PRIVATE_KEY***" in candidate.snippet

    def test_all_credential_pattern_kinds_have_a_dedicated_test_above(self) -> None:
        # Guards against silently missing a kind if CREDENTIAL_PATTERNS grows.
        exercised_kinds = {
            "PRIVATE_KEY",
            "OPENAI_KEY",
            "AWS_ACCESS_KEY",
            "GITHUB_TOKEN",
            "SLACK_TOKEN",
            "GENERIC_SECRET",
        }
        assert {name for name, _ in CREDENTIAL_PATTERNS} == exercised_kinds


class TestDedupeAndOrdering:
    def test_two_matches_of_the_same_kind_on_one_line_dedupe_to_one_candidate(self) -> None:
        text = 'a = "sk-abcdefghijklmnopqrstuvwx1234"; b = "sk-zzzzzzzzzzzzzzzzzzzzzzzzzzzz"\n'

        candidates = scan_text(text)

        matches = [c for c in candidates if c.kind == "OPENAI_KEY"]
        assert len(matches) == 1
        assert "sk-abcdefghijklmnopqrstuvwx1234" not in matches[0].snippet
        assert "sk-zzzzzzzzzzzzzzzzzzzzzzzzzzzz" not in matches[0].snippet

    def test_candidates_are_sorted_by_line_then_column(self) -> None:
        text = 'first = "AKIAIOSFODNN7EXAMPLE"\nsecond = "sk-abcdefghijklmnopqrstuvwx1234"\n'

        candidates = scan_text(text)

        positions = [(c.line, c.column) for c in candidates]
        assert positions == sorted(positions)


class TestEntropyPass:
    def test_real_random_secret_flagged_as_high_entropy(self) -> None:
        # No sk-/AKIA/ghp_/xox prefix and no key="..." context, so this can
        # ONLY be caught by the entropy pass -- exactly the case it exists for.
        secret = "kP3xQ9zR7mNv2LsT8wYbF4jHcD6gA1eU5oIx9Z"
        text = f"config_value = {secret}\n"

        candidates = scan_text(text)

        assert len(candidates) == 1
        candidate = candidates[0]
        assert candidate.kind == "high_entropy"
        assert candidate.line == 1
        assert candidate.column == text.index(secret) + 1
        assert candidate.entropy is not None
        assert candidate.entropy >= 4.0
        assert secret not in candidate.snippet  # the critical leak check

    def test_regex_covered_secret_not_also_double_flagged_as_high_entropy(self) -> None:
        # "sk-abcdefghijklmnopqrstuvwx1234" is itself high-entropy (>4 bits/char)
        # -- if the entropy pass ignored the "already regex-covered" rule, this
        # line would produce BOTH an OPENAI_KEY row and a high_entropy row for
        # the same secret. The variable name deliberately avoids the
        # GENERIC_SECRET label words (api_key/secret/token/password) so only
        # OPENAI_KEY's pattern fires here.
        secret = "sk-abcdefghijklmnopqrstuvwx1234"
        assert shannon_entropy(secret) >= 4.0  # precondition for this test to be meaningful
        text = f'SOME_ENV_VAR = "{secret}"\n'

        candidates = scan_text(text)

        assert [c.kind for c in candidates] == ["OPENAI_KEY"]

    def test_low_entropy_english_compound_identifier_never_flagged(self) -> None:
        # A realistic long lowercase identifier: 28 chars (>= min_token_len)
        # but ordinary English/code letter-frequency keeps entropy ~3.47 bits/
        # char, safely under the 4.0 default threshold.
        token = "authentication_configuration"
        assert shannon_entropy(token) < 4.0  # precondition for this test to be meaningful
        text = f"setting_name = {token}\n"

        candidates = scan_text(text)

        assert candidates == []

    def test_base64_png_header_line_surfaces_as_high_entropy_for_llm_to_dismiss(self) -> None:
        # A real 1x1-transparent-PNG data URI body -- not a credential by any
        # stretch, but base64's wide (64-symbol) alphabet pushes its Shannon
        # entropy (~4.15 bits/char) above the default 4.0 threshold. This is
        # INTENTIONAL high recall: the local scanner is not the trust
        # boundary, and Hy3's triage step is expected to dismiss this as a
        # false positive.
        png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
            "+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        assert shannon_entropy(png_b64) >= 4.0
        text = f"data_uri = {png_b64}\n"

        candidates = scan_text(text)

        assert len(candidates) == 1
        assert candidates[0].kind == "high_entropy"
        assert png_b64 not in candidates[0].snippet

    def test_git_sha_hex_digest_not_flagged_at_the_default_threshold(self) -> None:
        # Pure hex content (16-symbol alphabet) has a hard Shannon-entropy
        # CEILING of log2(16) == 4.0 bits/char, and a real 40-char hex digest
        # measures well below that ceiling in practice (~3.8 bits/char here)
        # -- so it will NOT cross the default min_entropy=4.0 threshold. This
        # is a mathematical property of the hex alphabet, not a scanner gap.
        git_sha = "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        assert shannon_entropy(git_sha) < 4.0
        text = f"parent {git_sha}\n"

        assert scan_text(text) == []

    def test_git_sha_hex_digest_surfaces_as_high_entropy_when_threshold_tuned_for_hex(
        self,
    ) -> None:
        # An operator who wants to also catch hex-alphabet secrets (or who
        # accepts git SHAs / lockfile checksums as an intentional high-recall
        # false positive) tunes min_entropy down towards the hex ceiling.
        # Doing so surfaces this same line as a high_entropy candidate --
        # exactly the "intentionally high-recall, Hy3 dismisses it" behavior
        # documented above for the base64 case, now demonstrated for hex too.
        git_sha = "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3"
        text = f"parent {git_sha}\n"

        candidates = scan_text(text, min_entropy=3.5)

        assert len(candidates) == 1
        assert candidates[0].kind == "high_entropy"
        assert git_sha not in candidates[0].snippet

    def test_short_high_entropy_token_below_min_token_len_not_flagged(self) -> None:
        text = "x = aB3$fooShort\n"  # well under 20 chars either way

        assert scan_text(text) == []


class TestUnquotedAssignmentSecrets:
    """The entropy pass is the safety net for novel, non-pattern-shaped
    secrets. A tight, unquoted ``LABEL=secret`` (env-var / Dockerfile ENV /
    shell export shape) is exactly what GENERIC_SECRET's quote-requiring
    regex does NOT catch, so the entropy pass MUST tokenize the value
    independently of the label -- otherwise a long, low-diversity label
    dilutes the combined entropy below threshold and the secret is missed.
    """

    _SECRET = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8"  # entropy ~4.73 on its own
    _LABEL = "X" * 60  # long + zero-diversity: drags the merged token's entropy down

    def test_equals_separated_secret_is_flagged_not_diluted_by_label(self) -> None:
        # Precondition: the value alone is high-entropy, but merged with the
        # label the combined token dips well under threshold -- so a tokenizer
        # that keeps them joined would silently miss this real secret.
        assert shannon_entropy(self._SECRET) >= 4.0
        assert shannon_entropy(f"{self._LABEL}={self._SECRET}") < 4.0
        text = f"{self._LABEL}={self._SECRET}\n"

        candidates = scan_text(text)

        assert len(candidates) == 1
        assert candidates[0].kind == "high_entropy"
        assert self._SECRET not in candidates[0].snippet  # value still masked
        assert "***REDACTED-HIGH_ENTROPY***" in candidates[0].snippet

    def test_colon_separated_secret_is_flagged_not_diluted_by_label(self) -> None:
        # Same property for the ``KEY:secret`` separator shape (YAML/config).
        text = f"{self._LABEL}:{self._SECRET}\n"

        candidates = scan_text(text)

        assert len(candidates) == 1
        assert candidates[0].kind == "high_entropy"
        assert self._SECRET not in candidates[0].snippet

    def test_base64_value_with_equals_padding_still_flagged(self) -> None:
        # Splitting the token on '=' must NOT hurt base64 recall: '=' is only
        # trailing padding, carries no entropy, so the body's entropy is
        # essentially unchanged and still above threshold after the split.
        png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
            "+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        text = f"data_uri = {png_b64}\n"

        candidates = scan_text(text)

        assert len(candidates) == 1
        assert candidates[0].kind == "high_entropy"
        # The raw base64 body (with or without its '=' padding) must be masked.
        assert png_b64 not in candidates[0].snippet
        assert png_b64.rstrip("=") not in candidates[0].snippet


class TestNoRawSecretLeak:
    """Cross-cutting proof: whatever candidates come back, the raw planted
    secret string never appears in any of their snippets."""

    def test_high_entropy_secret_absent_from_every_snippet(self) -> None:
        secret = "kP3xQ9zR7mNv2LsT8wYbF4jHcD6gA1eU5oIx9Z"
        text = f"line0\nconfig_value = {secret}\nline2\n"

        candidates = scan_text(text)

        assert candidates  # sanity: the detector actually ran
        for candidate in candidates:
            assert secret not in candidate.snippet

    def test_regex_secret_absent_from_every_snippet(self) -> None:
        secret = "AKIAIOSFODNN7EXAMPLE"
        text = f'aws_key = "{secret}"\n'

        candidates = scan_text(text)

        assert candidates
        for candidate in candidates:
            assert secret not in candidate.snippet


class TestCoLocatedEntropySecretMasking:
    """A line can carry BOTH a known-shape credential (regex-matched) AND a
    second, entropy-only secret that matches no CREDENTIAL_PATTERNS shape --
    e.g. a realistic inline `AWS_ACCESS_KEY_ID:AWS_SECRET_ACCESS_KEY` pair.
    redact() alone only knows CREDENTIAL_PATTERNS shapes, so without an
    entropy pass over the regex candidate's own span too, the co-located
    secret survives raw into the snippet -- even though the line is marked
    regex-covered (so the entropy pass never runs on it separately)."""

    _AWS_SECRET = "wJalrXUtnFEMIbKR7MDENGbPxRfiCYEXAMPLEKEY"

    def test_co_located_secret_absent_from_regex_candidate_snippet(self) -> None:
        assert shannon_entropy(self._AWS_SECRET) >= 4.0  # precondition
        text = f'aws = "AKIAIOSFODNN7EXAMPLE:{self._AWS_SECRET}"\n'

        candidates = scan_text(text)

        assert candidates  # sanity: the detector actually ran
        for candidate in candidates:
            assert self._AWS_SECRET not in candidate.snippet

    def test_known_shape_credential_still_gets_its_named_mask(self) -> None:
        # The known-shape half of the pair must still be redacted under its
        # own pattern name -- entropy-masking the co-located secret must not
        # regress the existing named-mask guarantee.
        text = f'aws = "AKIAIOSFODNN7EXAMPLE:{self._AWS_SECRET}"\n'

        candidates = scan_text(text)

        matches = [c for c in candidates if c.kind == "AWS_ACCESS_KEY"]
        assert len(matches) == 1
        assert "***REDACTED-AWS_ACCESS_KEY***" in matches[0].snippet
        assert "AKIAIOSFODNN7EXAMPLE" not in matches[0].snippet


class TestEmptyInput:
    def test_empty_text_returns_empty_list(self) -> None:
        assert scan_text("") == []
