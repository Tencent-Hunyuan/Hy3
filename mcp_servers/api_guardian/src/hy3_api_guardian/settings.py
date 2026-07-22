"""Environment-only configuration for the MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigurationError


def _read_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value


def _read_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings loaded from environment variables."""

    api_key: str | None
    base_url: str
    model: str
    allowed_root: Path
    timeout_seconds: float
    max_retries: int
    max_file_bytes: int
    max_model_chars: int
    max_output_tokens: int
    reasoning_effort: str

    @classmethod
    def from_env(cls) -> Settings:
        root_value = os.getenv("HY3_ALLOWED_ROOT", str(Path.cwd())).strip()
        root = Path(root_value).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ConfigurationError("HY3_ALLOWED_ROOT must be an existing directory")

        base_url = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1").strip()
        if not base_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ConfigurationError(
                "HY3_BASE_URL must use HTTPS, except for localhost development endpoints"
            )

        effort = os.getenv("HY3_REASONING_EFFORT", "high").strip().lower()
        if effort not in {"no_think", "low", "high"}:
            raise ConfigurationError("HY3_REASONING_EFFORT must be one of: no_think, low, high")

        return cls(
            api_key=os.getenv("HY3_API_KEY") or None,
            base_url=base_url.rstrip("/"),
            model=os.getenv("HY3_MODEL", "hy3").strip() or "hy3",
            allowed_root=root,
            timeout_seconds=_read_float("HY3_TIMEOUT", 60.0, 1.0, 300.0),
            max_retries=_read_int("HY3_MAX_RETRIES", 2, 0, 5),
            max_file_bytes=_read_int("HY3_MAX_FILE_BYTES", 2_000_000, 1_024, 10_000_000),
            max_model_chars=_read_int("HY3_MAX_MODEL_CHARS", 120_000, 4_000, 500_000),
            max_output_tokens=_read_int("HY3_MAX_OUTPUT_TOKENS", 8_000, 256, 32_000),
            reasoning_effort=effort,
        )

    def require_api_key(self) -> str:
        if not self.api_key:
            raise ConfigurationError(
                "HY3_API_KEY is not set. Create a TokenHub key and pass it through the "
                "MCP client's environment configuration."
            )
        return self.api_key

    def safe_summary(self) -> dict[str, object]:
        """Return diagnostics that never include secret material."""
        return {
            "base_url": self.base_url,
            "model": self.model,
            "allowed_root": str(self.allowed_root),
            "api_key_present": bool(self.api_key),
            "timeout_seconds": self.timeout_seconds,
            "max_file_bytes": self.max_file_bytes,
        }
