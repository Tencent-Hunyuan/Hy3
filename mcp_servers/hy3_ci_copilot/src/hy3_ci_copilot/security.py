from __future__ import annotations

import re

_ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_AUTH_HEADER = re.compile(r"(?im)(\bauthorization\s*:\s*)(?:bearer|basic)\s+\S+")
_URL_CREDENTIALS = re.compile(
    r"(?i)((?:https?|postgres(?:ql)?|mysql|redis|rediss|amqp|amqps|"
    r"mongodb(?:\+srv)?)://[^\s/:]+:)[^\s/@]+(@)"
)
_SENSITIVE_BLOCK = re.compile(
    r"(?im)^(\s*(?:[\"']?)[A-Z0-9_.-]*"
    r"(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE[_-]?KEY)"
    r"[A-Z0-9_.-]*(?:[\"']?)\s*:\s*)[>|][+-]?[^\n]*\n"
    r"(?:[ \t]+[^\n]*(?:\n|$))+"
)
_SENSITIVE_ASSIGNMENT = re.compile(
    r"(?im)((?:[\"']?)\b[A-Z0-9_.-]*"
    r"(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE[_-]?KEY)"
    r"[A-Z0-9_.-]*\b(?:[\"']?)\s*[:=]\s*)"
    r"(?:\"[^\"\n]*\"|'[^'\n]*'|[^\s,;]+)"
)
_KNOWN_TOKEN = re.compile(
    r"(?i)\b(?:gh[pousr]_[A-Za-z0-9]{20,}|glpat-[A-Za-z0-9_-]{20,}|"
    r"sk-or-v1-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,}|"
    r"AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{20,}|npm_[A-Za-z0-9]{20,})\b"
)
_PEM_PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
    re.DOTALL,
)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")


def clean_terminal_text(text: str) -> str:
    """Remove terminal formatting and unsafe control characters."""
    text = _CONTROL_CHARS.sub("", _ANSI_ESCAPE.sub("", text))
    return text.replace("\r\n", "\n").replace("\r", "\n")


def redact_secrets(text: str) -> str:
    """Best-effort removal of common credentials before content reaches Hy3."""
    text = _PEM_PRIVATE_KEY.sub("[REDACTED PRIVATE KEY]", text)
    text = _SENSITIVE_BLOCK.sub(r"\1[REDACTED]\n", text)
    text = _AUTH_HEADER.sub(r"\1[REDACTED]", text)
    text = _URL_CREDENTIALS.sub(r"\1[REDACTED]\2", text)
    text = _SENSITIVE_ASSIGNMENT.sub(r"\1[REDACTED]", text)
    text = _KNOWN_TOKEN.sub("[REDACTED TOKEN]", text)
    return _JWT.sub("[REDACTED JWT]", text)


def sanitize_untrusted_text(text: str) -> str:
    return redact_secrets(clean_terminal_text(text))


def truncate_middle(text: str, limit: int, label: str = "content") -> str:
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    marker = f"... [{len(text):,} characters omitted from {label}] ..."
    if len(marker) >= limit:
        return marker[:limit]
    for _ in range(3):
        available = limit - len(marker)
        omitted = len(text) - available
        marker = f"\n\n... [{omitted:,} characters omitted from {label}] ...\n\n"
    if len(marker) >= limit:
        return marker[:limit]
    available = max(0, limit - len(marker))
    head = int(available * 0.4)
    tail = available - head
    return f"{text[:head]}{marker}{text[-tail:] if tail else ''}"
