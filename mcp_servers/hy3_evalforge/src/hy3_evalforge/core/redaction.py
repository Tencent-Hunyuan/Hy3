"""Credential detection and redaction before untrusted content leaves the process."""

from __future__ import annotations

import re
from collections.abc import Iterable

REDACTED_SECRET = "[REDACTED_SECRET]"

_PATTERNS = (
    re.compile(
        r"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----.*?-----END(?: [A-Z0-9]+)* PRIVATE KEY-----",
        re.DOTALL,
    ),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b", re.IGNORECASE),
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s'\"<>]+", re.IGNORECASE),
    re.compile(
        r"\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*[^\s,;]+", re.IGNORECASE
    ),
)


def redact_text(text: str, *, additional_secrets: Iterable[str] = ()) -> str:
    """Replace detected and explicitly supplied credentials with a stable marker."""
    redacted = text
    for secret in sorted({value for value in additional_secrets if value}, key=len, reverse=True):
        redacted = redacted.replace(secret, REDACTED_SECRET)
    for pattern in _PATTERNS:
        redacted = pattern.sub(REDACTED_SECRET, redacted)
    return redacted
