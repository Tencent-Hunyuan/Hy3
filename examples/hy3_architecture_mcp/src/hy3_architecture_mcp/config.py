"""Configuration loaded from environment variables.

The Hy3 model is served through an OpenAI-compatible API (vLLM / SGLang),
so none of HY3_API_KEY / HY3_BASE_URL / HY3_MODEL are strictly required for a
local deployment (they default to ``EMPTY`` / ``http://127.0.0.1:8000/v1`` /
``hy3``). They become required only when targeting a remote endpoint.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path

from pydantic import BaseModel, SecretStr, ValidationError, field_validator, model_validator

from .exceptions import ConfigurationError

# Reasoning-effort values accepted by the Hy3 chat template.
_REASONING_EFFORTS = {"no_think", "low", "high"}


class Settings(BaseModel):
    """Validated runtime configuration."""

    api_key: SecretStr = SecretStr("EMPTY")
    base_url: str = "http://127.0.0.1:8000/v1"
    model: str = "hy3"
    reasoning_effort: str = "high"
    timeout_seconds: float = 60.0
    max_retries: int = 2
    workspace_root: Path | None = None
    max_file_size_bytes: int = 1_048_576
    max_total_size_bytes: int = 5_242_880

    @field_validator("base_url")
    @classmethod
    def _strip_base_url(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("HY3_BASE_URL must not be empty")
        return v.strip().rstrip("/")

    @field_validator("model")
    @classmethod
    def _strip_model(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("HY3_MODEL must not be empty")
        return v.strip()

    @field_validator("reasoning_effort")
    @classmethod
    def _reasoning_effort(cls, v: str) -> str:
        v = (v or "high").strip()
        if v not in _REASONING_EFFORTS:
            raise ValueError(f"HY3_REASONING_EFFORT must be one of {sorted(_REASONING_EFFORTS)}")
        return v

    @field_validator("timeout_seconds")
    @classmethod
    def _timeout_range(cls, v: float) -> float:
        if v <= 0 or v > 600:
            raise ValueError("HY3_TIMEOUT_SECONDS must be in (0, 600]")
        return v

    @field_validator("max_retries")
    @classmethod
    def _retries_range(cls, v: int) -> int:
        if v < 0 or v > 10:
            raise ValueError("HY3_MAX_RETRIES must be in [0, 10]")
        return v

    @field_validator("max_file_size_bytes")
    @classmethod
    def _max_file(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("HY3_MAX_FILE_SIZE_BYTES must be > 0")
        return v

    @field_validator("max_total_size_bytes")
    @classmethod
    def _max_total(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("HY3_MAX_TOTAL_SIZE_BYTES must be > 0")
        return v

    @model_validator(mode="after")
    def _normalize_workspace(self) -> Settings:
        if self.workspace_root is not None:
            # Resolve to a canonical absolute path (expands ~ , normalises separators).
            self.workspace_root = self.workspace_root.expanduser().resolve()
        return self

    # Convenience -----------------------------------------------------------

    def require_workspace_root(self) -> Path:
        """Return the workspace root or raise ConfigurationError if unset.

        Only the ``analyze_project_context`` tool needs a workspace root; the
        server can boot and the four core tools can run without one.
        """
        if self.workspace_root is None:
            raise ConfigurationError(
                "HY3_WORKSPACE_ROOT is not set. analyze_project_context needs an "
                "absolute path that bounds which local files it may read."
            )
        return self.workspace_root


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


@functools.lru_cache(maxsize=1)
def load_settings() -> Settings:
    """Load and validate settings from environment variables.

    Raises ConfigurationError with an actionable message if validation fails.
    """
    raw = {
        "api_key": _env("HY3_API_KEY", "EMPTY"),
        "base_url": _env("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
        "model": _env("HY3_MODEL", "hy3"),
        "reasoning_effort": _env("HY3_REASONING_EFFORT", "high"),
        # Pass strings; Pydantic coerces + validates (so "abc" -> ConfigurationError).
        "timeout_seconds": _env("HY3_TIMEOUT_SECONDS", "60"),
        "max_retries": _env("HY3_MAX_RETRIES", "2"),
        "workspace_root": _env("HY3_WORKSPACE_ROOT") or None,
        "max_file_size_bytes": _env("HY3_MAX_FILE_SIZE_BYTES", "1048576"),
        "max_total_size_bytes": _env("HY3_MAX_TOTAL_SIZE_BYTES", "5242880"),
    }
    try:
        return Settings(**raw)  # type: ignore[arg-type]
    except ValidationError as exc:
        # Collect human-friendly field-level messages.
        details = "; ".join(
            f"{'/'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise ConfigurationError(f"Invalid Hy3 MCP configuration: {details}") from None


def reset_settings_cache() -> None:
    """Clear the cached settings (used by tests that mutate environment)."""
    load_settings.cache_clear()
