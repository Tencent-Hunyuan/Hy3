"""Environment-backed configuration for the MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigurationError(RuntimeError):
    """Raised when required server configuration is missing or invalid."""


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false")


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings loaded only from environment variables."""

    base_url: str
    model: str
    api_key: str | None
    reasoning_effort: str
    temperature: float
    top_p: float
    max_tokens: int
    api_timeout_seconds: float
    search_timeout_seconds: float
    fetch_timeout_seconds: float
    max_page_chars: int
    allow_private_urls: bool

    @classmethod
    def from_env(cls) -> "Settings":
        reasoning_effort = os.getenv("HY3_REASONING_EFFORT", "high")
        if reasoning_effort not in {"no_think", "low", "high"}:
            raise ConfigurationError(
                "HY3_REASONING_EFFORT must be one of: no_think, low, high"
            )

        settings = cls(
            base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1").rstrip("/"),
            model=os.getenv("HY3_MODEL", "hy3"),
            api_key=os.getenv("HY3_API_KEY"),
            reasoning_effort=reasoning_effort,
            temperature=_float_env("HY3_TEMPERATURE", 0.9),
            top_p=_float_env("HY3_TOP_P", 1.0),
            max_tokens=_int_env("HY3_MAX_TOKENS", 8192),
            api_timeout_seconds=_float_env("HY3_API_TIMEOUT", 300.0),
            search_timeout_seconds=_float_env("RESEARCH_SEARCH_TIMEOUT", 20.0),
            fetch_timeout_seconds=_float_env("RESEARCH_FETCH_TIMEOUT", 20.0),
            max_page_chars=_int_env("RESEARCH_MAX_PAGE_CHARS", 20_000),
            allow_private_urls=_bool_env("RESEARCH_ALLOW_PRIVATE_URLS", False),
        )
        if not settings.base_url:
            raise ConfigurationError("HY3_BASE_URL cannot be empty")
        if not settings.model:
            raise ConfigurationError("HY3_MODEL cannot be empty")
        if settings.max_tokens < 1:
            raise ConfigurationError("HY3_MAX_TOKENS must be positive")
        if settings.max_page_chars < 1_000:
            raise ConfigurationError("RESEARCH_MAX_PAGE_CHARS must be at least 1000")
        return settings

    def require_api_key(self) -> str:
        """Return the configured key, failing only when a Hy3 tool is invoked."""

        if not self.api_key:
            raise ConfigurationError(
                "HY3_API_KEY is required for Hy3 analysis. "
                "Set it to your provider key, or to EMPTY for a local vLLM/SGLang endpoint."
            )
        return self.api_key
