class ConfigurationError(ValueError):
    """Raised when server configuration is missing or invalid."""


class AccessDeniedError(ValueError):
    """Raised when a requested path is outside the configured roots."""


class InputFileError(ValueError):
    """Raised when an input file cannot be processed safely."""


class Hy3APIError(RuntimeError):
    """Raised when the Hy3-compatible endpoint cannot complete a request."""
