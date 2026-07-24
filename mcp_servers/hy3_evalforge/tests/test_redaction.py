from hy3_evalforge.core.redaction import REDACTED_SECRET, redact_text


def test_redacts_detected_credentials_and_explicit_secrets() -> None:
    source = (
        "Authorization: Bearer abcdefghijklmnop; "
        "db=postgresql://user:pass@example.test/db; "
        "custom=very-secret-value"
    )

    result = redact_text(source, additional_secrets=("very-secret-value",))

    assert "abcdefghijklmnop" not in result
    assert "user:pass" not in result
    assert "very-secret-value" not in result
    assert result.count(REDACTED_SECRET) == 3


def test_redacts_pem_private_keys_without_mutating_normal_text() -> None:
    source = "keep this\n-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\nkeep that"

    assert redact_text(source) == f"keep this\n{REDACTED_SECRET}\nkeep that"
