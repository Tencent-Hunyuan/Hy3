"""Environment-only configuration for Hy3 EvalForge."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from hy3_evalforge.errors import ErrorCode, EvalForgeError


class Settings(BaseModel):
    """Validated runtime settings; API keys are never represented as plain strings."""

    model_config = ConfigDict(frozen=True)

    hy3_base_url: str = "http://127.0.0.1:8000/v1"
    hy3_model: str = "hy3"
    hy3_api_key: SecretStr | None = None
    allowed_root: Path
    max_file_bytes: int = 10 * 1024 * 1024
    max_cases: int = 50
    max_output_characters: int = 32_000
    max_model_calls: int = 24
    batch_size: int = 4
    max_concurrency: int = 2
    request_timeout_seconds: float = 90.0
    retry_attempts: int = 2
    extra_secret_env_vars: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("allowed_root")
    @classmethod
    def allowed_root_must_exist(cls, value: Path) -> Path:
        resolved = value.expanduser().resolve(strict=False)
        if not resolved.is_dir():
            raise ValueError("EVALFORGE_ALLOWED_ROOT must be an existing directory")
        return resolved

    @field_validator("max_file_bytes", "max_cases", "max_output_characters", "max_model_calls")
    @classmethod
    def positive_integer(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be greater than zero")
        return value

    @field_validator("batch_size", "max_concurrency")
    @classmethod
    def non_negative_integer(cls, value: int) -> int:
        if value < 1:
            raise ValueError("must be greater than zero")
        return value

    @field_validator("retry_attempts")
    @classmethod
    def non_negative_retry_attempts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must not be negative")
        return value

    @field_validator("request_timeout_seconds")
    @classmethod
    def positive_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("must be greater than zero")
        return value

    @classmethod
    def from_environment(cls, environ: dict[str, str] | None = None) -> Settings:
        """Load all configuration from environment variables without logging secret values."""
        source = os.environ if environ is None else environ
        root = source.get("EVALFORGE_ALLOWED_ROOT")
        if not root:
            raise EvalForgeError(
                ErrorCode.CONFIG_ERROR,
                "Set EVALFORGE_ALLOWED_ROOT to an existing evaluation-project root directory.",
            )

        extra_secret_env_vars = tuple(
            name.strip()
            for name in source.get("EVALFORGE_REDACT_ENV_VARS", "").split(",")
            if name.strip()
        )
        try:
            return cls(
                hy3_base_url=source.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
                hy3_model=source.get("HY3_MODEL", "hy3"),
                hy3_api_key=SecretStr(source["HY3_API_KEY"]) if source.get("HY3_API_KEY") else None,
                allowed_root=Path(root),
                max_file_bytes=int(source.get("EVALFORGE_MAX_FILE_BYTES", 10 * 1024 * 1024)),
                max_cases=int(source.get("EVALFORGE_MAX_CASES", 50)),
                max_output_characters=int(source.get("EVALFORGE_MAX_OUTPUT_CHARS", 32_000)),
                max_model_calls=int(source.get("EVALFORGE_MAX_MODEL_CALLS", 24)),
                batch_size=int(source.get("EVALFORGE_BATCH_SIZE", 4)),
                max_concurrency=int(source.get("EVALFORGE_MAX_CONCURRENCY", 2)),
                request_timeout_seconds=float(source.get("EVALFORGE_REQUEST_TIMEOUT_SECONDS", 90)),
                retry_attempts=int(source.get("EVALFORGE_RETRY_ATTEMPTS", 2)),
                extra_secret_env_vars=extra_secret_env_vars,
            )
        except (TypeError, ValueError) as exc:
            raise EvalForgeError(
                ErrorCode.CONFIG_ERROR, "Invalid EvalForge environment configuration."
            ) from exc

    def extra_secret_values(self, environ: dict[str, str] | None = None) -> tuple[str, ...]:
        """Return configured extra secrets for redaction, omitting absent or blank variables."""
        source = os.environ if environ is None else environ
        return tuple(source[name] for name in self.extra_secret_env_vars if source.get(name))

    def require_hy3_api_key(self) -> str:
        """Return the API key only at the provider boundary, or a safe configuration error."""
        if self.hy3_api_key is None:
            raise EvalForgeError(
                ErrorCode.CONFIG_ERROR,
                "Set HY3_API_KEY before invoking a tool that uses the Hy3 provider.",
            )
        return self.hy3_api_key.get_secret_value()
