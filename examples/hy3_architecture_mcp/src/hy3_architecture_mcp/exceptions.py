"""Exception hierarchy for the Hy3 Architecture MCP Server.

All errors carry an actionable message and never include the API key,
authentication headers, or the full raw model response.
"""

from __future__ import annotations


class Hy3McpError(Exception):
    """Base class for every error raised by this server."""


class ConfigurationError(Hy3McpError):
    """Raised when required environment configuration is missing or invalid."""


class Hy3AuthenticationError(Hy3McpError):
    """Raised on HTTP 401 / 403 from the Hy3 endpoint."""


class Hy3RateLimitError(Hy3McpError):
    """Raised on HTTP 429 after retries are exhausted."""


class Hy3TimeoutError(Hy3McpError):
    """Raised when a request to the Hy3 endpoint times out."""


class Hy3APIError(Hy3McpError):
    """Raised for other non-success status codes or transport failures."""


class ModelOutputError(Hy3McpError):
    """Raised when Hy3 output cannot be parsed into the expected schema
    even after one structured-repair retry."""


class WorkspaceAccessError(Hy3McpError):
    """Raised when a requested path is outside the workspace sandbox."""


class FileTooLargeError(Hy3McpError):
    """Raised when a file or the total read size exceeds configured limits."""


class InvalidToolInputError(Hy3McpError):
    """Raised when tool input fails semantic validation not caught by Pydantic."""


def mask(value: str, keep: int = 2) -> str:
    """Return a masked representation suitable for logs and error messages."""
    if not value:
        return "<empty>"
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * (len(value) - keep)
