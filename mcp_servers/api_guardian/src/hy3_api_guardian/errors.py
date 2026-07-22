"""Domain errors with messages safe to expose to MCP clients."""


class GuardianError(Exception):
    """Base error for expected, user-actionable failures."""


class ConfigurationError(GuardianError):
    """Raised when required environment configuration is missing or invalid."""


class SpecInputError(GuardianError):
    """Raised when an OpenAPI input cannot be loaded or validated."""


class ProviderError(GuardianError):
    """Raised when the Hy3 provider request fails."""
