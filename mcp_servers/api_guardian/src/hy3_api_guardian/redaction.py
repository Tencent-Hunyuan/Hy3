"""Best-effort secret redaction before content is sent to Hy3."""

from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

_PATTERNS = (
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[A-Za-z0-9._~+\-/]{8,}"),
    re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+\-/]{8,}"),
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)(https?://[^:/\s]+:)[^@/\s]+@"),
)

_SENSITIVE_VALUE_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "authorization",
    "client_secret",
    "password",
    "refresh_token",
    "secret",
    "token",
}


def redact_text(value: str) -> str:
    """Remove common credential forms from arbitrary text."""
    result = value
    for pattern in _PATTERNS:
        if pattern.groups:
            result = pattern.sub(lambda match: f"{match.group(1)}{REDACTED}", result)
        else:
            result = pattern.sub(REDACTED, result)
    return result


def redact_structure(value: Any) -> Any:
    """Recursively redact scalar values stored under explicitly sensitive keys."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in _SENSITIVE_VALUE_KEYS and not isinstance(item, (dict, list)):
                redacted[str(key)] = REDACTED
            else:
                redacted[str(key)] = redact_structure(item)
        return redacted
    if isinstance(value, list):
        return [redact_structure(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
