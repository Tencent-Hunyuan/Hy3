from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from dotenv import load_dotenv
from openai import OpenAI


Backend = Literal["self_hosted", "openrouter"]
ReasoningEffort = Literal["no_think", "low", "high"]
API_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Hy3Config:
    backend: Backend
    base_url: str
    api_key: str
    model: str
    timeout: float

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> Hy3Config:
        backend = str(values.get("HY3_BACKEND", "self_hosted")).strip()
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

        base_url = str(values.get("HY3_BASE_URL", default_base_url)).strip().rstrip("/")
        api_key = str(values.get("HY3_API_KEY", default_api_key)).strip()
        model = str(values.get("HY3_MODEL", default_model)).strip()

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
