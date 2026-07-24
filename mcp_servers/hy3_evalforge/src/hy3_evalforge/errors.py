"""Safe, actionable domain errors exposed by EvalForge tools."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from hy3_evalforge.core.redaction import redact_text


class ErrorCode(StrEnum):
    """Stable error codes defined by the frozen EvalForge design."""

    CONFIG_ERROR = "CONFIG_ERROR"
    INPUT_ERROR = "INPUT_ERROR"
    PATH_DENIED = "PATH_DENIED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    HY3_OUTPUT_INVALID = "HY3_OUTPUT_INVALID"
    EVIDENCE_INVALID = "EVIDENCE_INVALID"
    ARTIFACT_CONFLICT = "ARTIFACT_CONFLICT"


_SENSITIVE_DETAIL_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "password",
        "private_key",
        "prompt",
        "provider_response",
        "response_body",
        "response",
        "body",
        "headers",
        "content",
        "output",
        "secret",
        "token",
    }
)


def _safe_details(details: dict[str, Any] | None) -> dict[str, Any]:
    """Return diagnostic metadata without values that may contain secrets or prompts."""
    if details is None:
        return {}

    safe: dict[str, Any] = {}
    for key, value in details.items():
        normalized_key = key.lower()
        if normalized_key in _SENSITIVE_DETAIL_KEYS or any(
            fragment in normalized_key for fragment in ("secret", "token", "password", "key")
        ):
            safe[key] = "[REDACTED]"
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = redact_text(value)[:256] if isinstance(value, str) else value
        else:
            safe[key] = "[OMITTED]"
    return safe


class EvalForgeError(Exception):
    """An expected error that can be safely rendered as structured tool output."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = _safe_details(details)

    def to_payload(self) -> dict[str, Any]:
        """Serialize the error without exception internals or sensitive diagnostics."""
        return {
            "error": {"code": self.code.value, "message": self.message, "details": self.details}
        }
