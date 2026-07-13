"""Runtime configuration for the Hy3 Repo Scout example."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "tencent/hy3:free"


class ConfigError(ValueError):
    """Raised when Repo Scout configuration is missing or invalid."""


def _is_openrouter(base_url: str) -> bool:
    hostname = (urlparse(base_url).hostname or "").casefold()
    return hostname == "openrouter.ai" or hostname.endswith(".openrouter.ai")


def _read_int(
    env: Mapping[str, str], name: str, default: int, *, minimum: int = 1
) -> int:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}")
    return value


def _read_float(
    env: Mapping[str, str], name: str, default: float, *, minimum: float = 0.0
) -> float:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be at least {minimum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated settings shared by the client, agent, and CLI."""

    api_key: str = field(repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = 90.0
    max_attempts: int = 3
    retry_base_delay: float = 0.5
    retry_max_delay: float = 8.0
    max_rounds: int = 9
    max_tool_calls: int = 32
    max_context_chars: int = 120_000
    max_tool_result_chars: int = 24_000
    max_tokens: int = 16_384
    temperature: float = 0.3
    top_p: float = 1.0
    reasoning_effort: str = "high"

    def __post_init__(self) -> None:
        base_url = self.base_url.strip().rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError("HY3_BASE_URL must be an absolute http(s) URL")
        object.__setattr__(self, "base_url", base_url)

        api_key = self.api_key.strip()
        if not api_key:
            raise ConfigError(
                "HY3_API_KEY is required (OPENROUTER_API_KEY is also accepted)"
            )
        if api_key.upper() == "EMPTY" and _is_openrouter(base_url):
            raise ConfigError("OpenRouter requires a real HY3_API_KEY or OPENROUTER_API_KEY")
        object.__setattr__(self, "api_key", api_key)

        model = self.model.strip()
        if not model:
            raise ConfigError("HY3_MODEL must not be empty")
        object.__setattr__(self, "model", model)

        positive_values = {
            "max_attempts": self.max_attempts,
            "max_rounds": self.max_rounds,
            "max_tool_calls": self.max_tool_calls,
            "max_context_chars": self.max_context_chars,
            "max_tool_result_chars": self.max_tool_result_chars,
            "max_tokens": self.max_tokens,
        }
        for name, value in positive_values.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ConfigError(f"{name} must be a positive integer")
        if self.max_rounds < 3:
            raise ConfigError("max_rounds must be at least 3")
        float_values = {
            "timeout": self.timeout,
            "retry_base_delay": self.retry_base_delay,
            "retry_max_delay": self.retry_max_delay,
            "temperature": self.temperature,
            "top_p": self.top_p,
        }
        for name, value in float_values.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ConfigError(f"{name} must be a finite number")
        if self.timeout <= 0:
            raise ConfigError("timeout must be greater than zero")
        if self.retry_base_delay < 0:
            raise ConfigError("retry_base_delay must not be negative")
        if self.retry_max_delay < self.retry_base_delay:
            raise ConfigError("retry_max_delay must be at least retry_base_delay")
        if not 0.0 <= self.temperature <= 2.0:
            raise ConfigError("temperature must be between 0 and 2")
        if not 0.0 < self.top_p <= 1.0:
            raise ConfigError("top_p must be greater than 0 and at most 1")
        if self.reasoning_effort not in {"no_think", "low", "high"}:
            raise ConfigError(
                "reasoning_effort must be one of: no_think, low, high"
            )
        if self.max_tool_result_chars < 256:
            raise ConfigError("max_tool_result_chars must be at least 256")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Load configuration without mutating or logging the environment."""

        env = os.environ if environ is None else environ
        base_url = env.get("HY3_BASE_URL", DEFAULT_BASE_URL)
        api_key = env.get("HY3_API_KEY", "").strip()
        if not api_key or (api_key.upper() == "EMPTY" and _is_openrouter(base_url)):
            fallback_key = env.get("OPENROUTER_API_KEY", "").strip()
            if fallback_key:
                api_key = fallback_key

        reasoning_effort = env.get("HY3_REASONING_EFFORT", "high").strip().lower()
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=env.get("HY3_MODEL", DEFAULT_MODEL),
            timeout=_read_float(env, "HY3_TIMEOUT", 90.0, minimum=0.001),
            max_attempts=_read_int(env, "HY3_MAX_ATTEMPTS", 3),
            retry_base_delay=_read_float(
                env, "HY3_RETRY_BASE_DELAY", 0.5, minimum=0.0
            ),
            retry_max_delay=_read_float(
                env, "HY3_RETRY_MAX_DELAY", 8.0, minimum=0.0
            ),
            max_rounds=_read_int(env, "HY3_MAX_ROUNDS", 9, minimum=3),
            max_tool_calls=_read_int(env, "HY3_MAX_TOOL_CALLS", 32),
            max_context_chars=_read_int(env, "HY3_MAX_CONTEXT_CHARS", 120_000),
            max_tool_result_chars=_read_int(
                env, "HY3_MAX_TOOL_RESULT_CHARS", 24_000, minimum=256
            ),
            max_tokens=_read_int(env, "HY3_MAX_TOKENS", 16_384),
            temperature=_read_float(env, "HY3_TEMPERATURE", 0.3),
            top_p=_read_float(env, "HY3_TOP_P", 1.0, minimum=0.001),
            reasoning_effort=reasoning_effort,
        )


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Convenience wrapper used by command-line entry points."""

    return Settings.from_env(environ)
