from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from dotenv import load_dotenv
from openai import OpenAI


Backend = Literal["self_hosted", "openrouter"]
ReasoningEffort = Literal["no_think", "low", "high"]
API_DIR = Path(__file__).resolve().parent


def _string_setting(values: Mapping[str, str], name: str, default: str) -> str:
    value = values.get(name, default)
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    return value.strip()


@dataclass(frozen=True)
class Hy3Config:
    backend: Backend
    base_url: str
    api_key: str = field(repr=False)
    model: str
    timeout: float

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> Hy3Config:
        backend = _string_setting(values, "HY3_BACKEND", "self_hosted")
        if backend not in ("self_hosted", "openrouter"):
            raise ValueError("HY3_BACKEND must be self_hosted or openrouter")

        if backend == "self_hosted":
            default_base_url = "http://127.0.0.1:8000/v1"
            default_api_key = "EMPTY"
            default_model = "hy3"
        else:
            default_base_url = "https://openrouter.ai/api/v1"
            default_api_key = ""
            default_model = "tencent/hy3:free"

        base_url = _string_setting(values, "HY3_BASE_URL", default_base_url).rstrip("/")
        api_key = _string_setting(values, "HY3_API_KEY", default_api_key)
        model = _string_setting(values, "HY3_MODEL", default_model)

        if not base_url:
            raise ValueError("HY3_BASE_URL must not be empty")
        if not api_key or (backend == "openrouter" and api_key == "EMPTY"):
            raise ValueError("HY3_API_KEY must contain a valid API key")
        if not model:
            raise ValueError("HY3_MODEL must not be empty")

        try:
            timeout = float(values.get("HY3_TIMEOUT", 120))
        except (TypeError, ValueError):
            raise ValueError("HY3_TIMEOUT must be a finite positive number") from None
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("HY3_TIMEOUT must be a finite positive number")

        return cls(
            backend=backend,
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )

    @classmethod
    def from_env(cls) -> Hy3Config:
        load_dotenv(API_DIR / ".env", override=False)
        return cls.from_mapping(os.environ)


def create_client(config: Hy3Config, *, max_retries: int = 2) -> OpenAI:
    return OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
        max_retries=max_retries,
    )


def reasoning_extra_body(
    config: Hy3Config, effort: ReasoningEffort
) -> dict[str, dict[str, str]]:
    if effort not in ("no_think", "low", "high"):
        raise ValueError("effort must be no_think, low, or high")

    if config.backend == "openrouter":
        mapped_effort = "none" if effort == "no_think" else effort
        return {"reasoning": {"effort": mapped_effort}}

    return {"chat_template_kwargs": {"reasoning_effort": effort}}


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)

    direct_value = getattr(value, name, None)
    if direct_value is not None:
        return direct_value

    model_extra = getattr(value, "model_extra", None)
    if isinstance(model_extra, Mapping):
        return model_extra.get(name, default)

    return default


def object_to_dict(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): object_to_dict(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [object_to_dict(item) for item in value]
    if is_dataclass(value):
        return object_to_dict(asdict(value))

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return object_to_dict(model_dump(exclude_none=True))

    attributes = getattr(value, "__dict__", None)
    if isinstance(attributes, Mapping):
        return {
            str(name): object_to_dict(item)
            for name, item in attributes.items()
            if not str(name).startswith("_") and item is not None
        }

    return str(value)


def extract_reasoning(message: Any) -> tuple[str, list[Any]]:
    reasoning = _field(message, "reasoning") or _field(
        message, "reasoning_content"
    )
    reasoning = str(reasoning or "")

    raw_details = _field(message, "reasoning_details")
    normalized_details = object_to_dict(raw_details)
    if normalized_details is None:
        details: list[Any] = []
    elif isinstance(normalized_details, list):
        details = normalized_details
    else:
        details = [normalized_details]

    if not reasoning:
        reasoning = "".join(
            str(detail["text"])
            for detail in details
            if isinstance(detail, Mapping) and detail.get("text") is not None
        )

    return reasoning, details


def assistant_message_to_dict(message: Any) -> dict[str, Any]:
    normalized = object_to_dict(message)
    if not isinstance(normalized, dict):
        raise TypeError("assistant message must serialize to an object")

    normalized.pop("model_extra", None)
    if normalized.get("role") is None:
        normalized["role"] = "assistant"

    model_extra = getattr(message, "model_extra", None)
    if isinstance(model_extra, Mapping):
        for name in ("reasoning", "reasoning_content", "reasoning_details"):
            value = model_extra.get(name)
            if value is not None and normalized.get(name) is None:
                normalized[name] = object_to_dict(value)

    return {name: value for name, value in normalized.items() if value is not None}


def summarize_completion(completion: Any) -> dict[str, Any]:
    choices = _field(completion, "choices", [])
    if not choices:
        raise RuntimeError("completion did not contain any choices")

    choice = choices[0]
    message = _field(choice, "message")
    reasoning, reasoning_details = extract_reasoning(message)
    return {
        "model": _field(completion, "model"),
        "content": _field(message, "content"),
        "reasoning": reasoning,
        "reasoning_details": reasoning_details,
        "finish_reason": _field(choice, "finish_reason"),
        "usage": object_to_dict(_field(completion, "usage")),
    }


def print_json(label: str, value: Any) -> None:
    print(f"{label}:")
    print(json.dumps(object_to_dict(value), ensure_ascii=False, indent=2))
