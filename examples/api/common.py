"""Shared configuration and response helpers for the Hy3 API examples."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
DEFAULT_MODEL = "hy3"


@dataclass(frozen=True)
class ApiConfig:
    """Connection settings loaded from environment variables."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL


def load_config() -> ApiConfig:
    """Load `.env` next to the examples, then validate required settings."""

    load_dotenv(Path(__file__).with_name(".env"))
    api_key = os.getenv("HY3_API_KEY", "").strip()
    if not api_key or api_key == "replace-with-your-api-key":
        raise SystemExit(
            "HY3_API_KEY is missing. Copy .env.example to .env and set the key, "
            "or export HY3_API_KEY in the shell."
        )

    return ApiConfig(
        api_key=api_key,
        base_url=os.getenv("HY3_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        model=os.getenv("HY3_MODEL", DEFAULT_MODEL),
    )


def create_client(
    config: ApiConfig,
    *,
    timeout: float = 60.0,
    max_retries: int = 2,
) -> OpenAI:
    """Create an OpenAI-compatible client for TokenHub or a self-hosted server."""

    return OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=timeout,
        max_retries=max_retries,
    )


def get_extra_field(value: Any, name: str, default: Any = None) -> Any:
    """Read a normal or provider-specific field from an SDK response model."""

    direct = getattr(value, name, None)
    if direct is not None:
        return direct
    model_extra = getattr(value, "model_extra", None) or {}
    return model_extra.get(name, default)


def model_dump(value: Any) -> Any:
    """Convert an SDK model into plain Python values when possible."""

    if value is None:
        return None
    if isinstance(value, list):
        return [model_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: model_dump(item) for key, item in value.items()}
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return model_dump(dump(exclude_none=True))
    return value


def usage_dict(response_or_chunk: Any) -> dict[str, Any] | None:
    """Return usage as a serializable dictionary when the response contains it."""

    usage = getattr(response_or_chunk, "usage", None)
    if usage is None:
        return None
    dumped = model_dump(usage)
    return dumped if isinstance(dumped, dict) else {"value": dumped}


def assistant_message_dict(message: Any) -> dict[str, Any]:
    """Serialize assistant state for the next request in a tool loop.

    TokenHub preserved-thinking tool calls require `reasoning_content` to be
    sent back together with `content` and `tool_calls`.
    """

    dumped = model_dump(message)
    if not isinstance(dumped, dict):
        raise TypeError("Assistant message cannot be serialized")

    result: dict[str, Any] = {"role": "assistant"}
    for field in ("content", "reasoning_content", "tool_calls"):
        value = dumped.get(field)
        if value is None:
            value = get_extra_field(message, field)
        if value is not None:
            result[field] = model_dump(value)
    return result
