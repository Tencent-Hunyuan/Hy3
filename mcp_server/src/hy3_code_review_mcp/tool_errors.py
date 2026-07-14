"""Stable, actionable MCP tool error results."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from mcp.types import CallToolResult, TextContent

from .config import ConfigurationError
from .git_service import GitServiceError
from .hy3_client import Hy3ClientError


@dataclass(frozen=True, slots=True)
class ToolErrorDetail:
    """Machine-readable error fields shared by all public tools."""

    code: str
    message: str
    suggested_action: str
    retryable: bool


def error_result(exc: Exception) -> CallToolResult:
    """Convert a known domain failure into an MCP error result."""
    if isinstance(exc, ConfigurationError):
        detail = ToolErrorDetail(
            code="CONFIGURATION_ERROR",
            message=str(exc),
            suggested_action=(
                "Set HY3_ENV_FILE or the required HY3_* environment variables, then run "
                "hy3-code-review-mcp --check-config."
            ),
            retryable=False,
        )
    elif isinstance(exc, GitServiceError):
        detail = ToolErrorDetail(
            code=exc.code,
            message=str(exc),
            suggested_action=exc.suggested_action,
            retryable=exc.retryable,
        )
    elif isinstance(exc, Hy3ClientError):
        detail = ToolErrorDetail(
            code=exc.code,
            message=str(exc),
            suggested_action=exc.suggested_action,
            retryable=exc.retryable,
        )
    else:
        detail = ToolErrorDetail(
            code="INTERNAL_ERROR",
            message="The MCP server encountered an unexpected internal error.",
            suggested_action=(
                "Check the server stderr log, retry once, and report the issue if it persists."
            ),
            retryable=False,
        )

    payload = {"ok": False, "error": asdict(detail)}
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            )
        ],
        structuredContent=payload,
        isError=True,
    )
