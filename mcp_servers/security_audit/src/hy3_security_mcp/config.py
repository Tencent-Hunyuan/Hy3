"""Configuration loading for the Hy3 API client.

Reads HY3_* environment variables only — no .env-file loading, no dotenv
dependency. MCP clients pass env vars in their config; for local dev use
`uv run --env-file`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

import pydantic

_ENV_API_KEY = "HY3_API_KEY"

# Maps Hy3Config field name -> source environment variable name, for
# overridable (non-required) fields.
_FIELD_TO_ENV: dict[str, str] = {
    "base_url": "HY3_BASE_URL",
    "model": "HY3_MODEL",
    "temperature": "HY3_TEMPERATURE",
    "max_tokens": "HY3_MAX_TOKENS",
    "timeout_seconds": "HY3_TIMEOUT_SECONDS",
}


class ConfigError(Exception):
    """Raised when Hy3 configuration is missing or invalid."""


class Hy3Config(pydantic.BaseModel):
    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str
    model: str = "tencent/hy3:free"
    temperature: float = 0.2
    # 8192: Hy3 is a reasoning model; on endpoints where the template doesn't
    # honor reasoning_effort=no_think, it spends the budget on hidden
    # reasoning tokens before ever emitting content. 2048 was empirically too
    # low (empty content, finish_reason='length'); 8192 completed a full
    # 108-case eval cleanly against tencent/hy3:free.
    max_tokens: int = 8192
    timeout_seconds: float = 120.0


def load_config(env: Mapping[str, str] | None = None) -> Hy3Config:
    """Load Hy3Config from environment variables (default: os.environ)."""
    source = env if env is not None else os.environ

    api_key = source.get(_ENV_API_KEY, "")
    if not api_key:
        raise ConfigError(
            f"{_ENV_API_KEY} is required — see .env.example for the three backend "
            "options (OpenRouter / Tencent Cloud / local vLLM)."
        )

    raw_fields: dict[str, str] = {"api_key": api_key}
    for field_name, env_name in _FIELD_TO_ENV.items():
        value = source.get(env_name)
        if value:
            raw_fields[field_name] = value

    try:
        return Hy3Config.model_validate(raw_fields)
    except pydantic.ValidationError as exc:
        error = exc.errors()[0]
        field_name = str(error["loc"][0])
        env_name = _FIELD_TO_ENV.get(field_name, field_name)
        bad_value = error.get("input")
        raise ConfigError(f"Invalid value for {env_name}: {bad_value!r} ({error['msg']})") from exc
