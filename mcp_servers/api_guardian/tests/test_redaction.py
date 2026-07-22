from __future__ import annotations

from hy3_api_guardian.redaction import REDACTED, redact_structure, redact_text


def test_redacts_common_credentials() -> None:
    text = "Authorization: Bearer abcdefghijklmnop and sk-abcdefghijklmnopqrstuvwxyz"
    result = redact_text(text)
    assert "abcdefghijklmnop" not in result
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in result
    assert REDACTED in result


def test_redacts_private_key_block() -> None:
    text = """before
-----BEGIN PRIVATE KEY-----
top-secret-material
-----END PRIVATE KEY-----
after"""
    result = redact_text(text)
    assert "top-secret-material" not in result
    assert result.startswith("before")
    assert result.endswith("after")


def test_redacts_sensitive_scalar_keys_but_keeps_schema_shape() -> None:
    value = {
        "token": "real-token-value",
        "schema": {"properties": {"api_key": {"type": "string"}}},
    }
    result = redact_structure(value)
    assert result["token"] == REDACTED
    assert result["schema"]["properties"]["api_key"]["type"] == "string"
