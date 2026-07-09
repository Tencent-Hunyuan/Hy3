"""Tests for redaction: CREDENTIAL_PATTERNS + redact().

Deterministic, no LLM involved — these prove the regex layer alone masks
realistic tokens while leaving surrounding code and benign identifiers alone.
"""

from __future__ import annotations

from hy3_security_mcp.redaction import CREDENTIAL_PATTERNS, redact


class TestNamedPatterns:
    def test_openai_key_redacted(self) -> None:
        text = 'OPENAI_API_KEY = "sk-abcdefghijklmnopqrstuvwx1234"\nnext_line = compute()'

        result = redact(text)

        assert "sk-abcdefghijklmnopqrstuvwx1234" not in result
        assert "***REDACTED-OPENAI_KEY***" in result
        assert "next_line = compute()" in result

    def test_aws_access_key_redacted(self) -> None:
        text = 'aws_key = "AKIAIOSFODNN7EXAMPLE"\nprint("done")'

        result = redact(text)

        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "***REDACTED-AWS_ACCESS_KEY***" in result
        assert 'print("done")' in result

    def test_github_token_redacted(self) -> None:
        text = "GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz1234\nreturn ok"

        result = redact(text)

        assert "ghp_abcdefghijklmnopqrstuvwxyz1234" not in result
        assert "***REDACTED-GITHUB_TOKEN***" in result
        assert "return ok" in result

    def test_slack_token_redacted(self) -> None:
        text = "SLACK_TOKEN=xoxb-1234567890-abcdefghij\nnext_stmt = 1"

        result = redact(text)

        assert "xoxb-1234567890-abcdefghij" not in result
        assert "***REDACTED-SLACK_TOKEN***" in result
        assert "next_stmt = 1" in result

    def test_generic_secret_assignment_redacted(self) -> None:
        text = 'password = "hunter2trustno1"\nnext_stmt = compute()'

        result = redact(text)

        assert "hunter2trustno1" not in result
        assert "***REDACTED-GENERIC_SECRET***" in result
        assert "next_stmt = compute()" in result

    def test_generic_secret_matches_api_key_and_token_and_secret_variants(self) -> None:
        text = (
            'api_key: "abcdefgh12345678"\ntoken = "abcdefgh12345678"\nsecret="abcdefgh12345678"\n'
        )

        result = redact(text)

        assert "abcdefgh12345678" not in result
        assert result.count("***REDACTED-GENERIC_SECRET***") == 3

    def test_private_key_block_fully_redacted_not_just_header(self) -> None:
        # A PEM private key is header + multi-line base64 body + footer. The
        # WHOLE block must collapse to one marker — redacting only the header
        # would leak the actual key material (the body) to the LLM.
        body_lines = (
            "MIIEpAIBAAKCAQEA1234567890abcdefGHIJKLMNOPqrstuvwx",
            "yzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/aBcDeFgHiJ",
            "kLmNoPqRsTuVwXyZ9876543210zzzzzzzzzzzzzzzzzz==",
        )
        text = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            + "\n".join(body_lines)
            + "\n-----END RSA PRIVATE KEY-----"
        )

        result = redact(text)

        assert result == "***REDACTED-PRIVATE_KEY***"
        for body_line in body_lines:
            assert body_line not in result
        assert "-----BEGIN RSA PRIVATE KEY-----" not in result
        assert "-----END RSA PRIVATE KEY-----" not in result

    def test_private_key_block_redacted_with_surrounding_code_intact(self) -> None:
        text = (
            "config = load()\n"
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAAB\n"
            "-----END OPENSSH PRIVATE KEY-----\n"
            "return config\n"
        )

        result = redact(text)

        assert "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAAB" not in result
        assert "***REDACTED-PRIVATE_KEY***" in result
        assert "config = load()" in result
        assert "return config" in result

    def test_two_private_key_blocks_redacted_independently(self) -> None:
        # Non-greedy matching: two blocks must NOT merge into one span that
        # swallows the text between them.
        text = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "FIRSTkeyBodyAAA111bbb222ccc333\n"
            "-----END RSA PRIVATE KEY-----\n"
            "some harmless code between the keys\n"
            "-----BEGIN EC PRIVATE KEY-----\n"
            "SECONDkeyBodyDDD444eee555fff666\n"
            "-----END EC PRIVATE KEY-----"
        )

        result = redact(text)

        assert result.count("***REDACTED-PRIVATE_KEY***") == 2
        assert "FIRSTkeyBodyAAA111bbb222ccc333" not in result
        assert "SECONDkeyBodyDDD444eee555fff666" not in result
        assert "some harmless code between the keys" in result

    def test_private_key_block_with_inner_awslike_run_not_carved(self) -> None:
        # A base64 body can coincidentally contain an AWS-key-shaped run
        # (AKIA + 16 upper/digits). The PEM block is the widest, highest-
        # confidence span, so it must collapse to a single PRIVATE_KEY marker,
        # NOT be carved into pieces by the inner AWS match.
        text = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "AKIAABCDEFGHIJKLMNOP1234567890AB\n"
            "-----END RSA PRIVATE KEY-----"
        )

        result = redact(text)

        assert result == "***REDACTED-PRIVATE_KEY***"
        assert "AKIA" not in result


class TestBenignTextUnaffected:
    def test_short_identifiers_named_like_credentials_not_redacted(self) -> None:
        text = "token_count = 5\nsecret_sauce_ratio = 0.42\napi_key_name = 'field'\n"

        assert redact(text) == text

    def test_plain_code_without_credentials_unaffected(self) -> None:
        text = "def add(a: int, b: int) -> int:\n    return a + b\n"

        assert redact(text) == text


class TestOverlappingMatchesNeverLeak:
    """When two credential spans overlap, NO secret byte from either span may
    survive in plaintext — the resolution must trim, not drop, the loser.
    """

    def test_narrow_key_nested_in_broad_secret_does_not_leak_tail(self) -> None:
        # AWS key (narrow, higher priority) sits inside a generic password value
        # (broad, lower priority). Dropping the whole generic match would leak
        # the value's tail after the AWS key.
        text = 'password = "AKIAABCDEFGHIJKLMNOPsomeOtherRandomSecretBytes1234!"'

        result = redact(text)

        assert "someOtherRandomSecretBytes1234!" not in result
        assert "AKIAABCDEFGHIJKLMNOP" not in result
        assert "***REDACTED-AWS_ACCESS_KEY***" in result

    def test_github_token_nested_in_generic_secret_does_not_leak_prefix(self) -> None:
        text = 'api_key = "myRealApplicationSecretValueXXYYZZghp_abcdefghijklmnopqrstuvwxyz1234"'

        result = redact(text)

        assert "myRealApplicationSecretValueXXYYZZ" not in result
        assert "ghp_abcdefghijklmnopqrstuvwxyz1234" not in result

    def test_partial_non_nested_overlap_does_not_leak(self) -> None:
        # SLACK stops at the '_' (not in its charset); OPENAI (which allows '_')
        # runs past it — the two spans partially overlap without nesting.
        # Dropping the lower-priority SLACK span would leak its 'xoxb-123456…'
        # prefix in plaintext.
        text = "xoxb-123456sk-aaaa_bbbbccccdddd"

        result = redact(text)

        assert "xoxb-123456" not in result
        assert "sk-aaaa_bbbbccccdddd" not in result

    def test_redact_is_idempotent(self) -> None:
        x = 'API_KEY = "sk-abcdefghijklmnopqrstuvwx1234"'

        once = redact(x)

        assert redact(once) == once


class TestCredentialPatternsShape:
    def test_pattern_names_are_unique(self) -> None:
        names = [name for name, _ in CREDENTIAL_PATTERNS]

        assert len(names) == len(set(names))

    def test_all_entries_are_name_and_compiled_pattern_pairs(self) -> None:
        import re

        for name, pattern in CREDENTIAL_PATTERNS:
            assert isinstance(name, str) and name
            assert isinstance(pattern, re.Pattern)
