"""Safe, actionable errors exposed by TaskRelay."""


class TaskRelayError(RuntimeError):
    """Base class for errors that are safe to show to an MCP caller."""


class TaskRelayInputError(TaskRelayError):
    """Raised when caller input cannot cross the Hy3 trust boundary safely."""


class Hy3OutputError(TaskRelayError):
    """Raised when Hy3 cannot produce a valid grounded structured result."""


class Hy3APIError(TaskRelayError):
    """Raised for safe-to-display Hy3 transport and API failures."""
