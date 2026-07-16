"""Tests for security: secret scrubbing and .gitignore enforcement."""
from __future__ import annotations

from ctxpilot.security import ensure_gitignore, sanitize


def test_sanitize_redacts_various_secrets():
    text = (
        "key=sk-abcdefghijklmnop\n"
        "aws=AKIA1234567890ABCD\n"
        "api_key='supersecretvalue'\n"
        "token=eyJhbGciOi.eyJzdWIi.xYz\n"
        "password='hunter2pass'\n"
        "Bearer eyJabc.def.ghi\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIB...\n-----END RSA PRIVATE KEY-----\n"
        "normal line stays"
    )
    out = sanitize(text)
    assert "sk-****" in out
    assert "AKIA****" in out
    assert "supersecretvalue" not in out
    assert "eyJhbGciOi" not in out
    assert "hunter2pass" not in out
    assert "PRIVATE KEY REDACTED" in out
    assert "normal line stays" in out


def test_sanitize_idempotent_on_clean_text():
    assert sanitize("nothing secret here") == "nothing secret here"


def test_ensure_gitignore_adds_and_is_idempotent(tmp_path):
    # first call adds
    assert ensure_gitignore(tmp_path) is True
    content = (tmp_path / ".gitignore").read_text()
    assert ".env" in content
    assert "HANDOFF.md" in content
    # second call is a no-op
    assert ensure_gitignore(tmp_path) is False
    # extra entry gets appended once
    assert ensure_gitignore(tmp_path, extra=(".mysecret",)) is True
    assert (tmp_path / ".gitignore").read_text().count(".mysecret") == 1
