from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv

ReasoningEffort = Literal["no_think", "low", "high"]


@dataclass(frozen=True)
class Hy3Settings:
    base_url: str = "https://tokenhub.tencentmaas.com/v1"
    api_key: str = "EMPTY"
    model: str = "hy3"
    default_reasoning_effort: ReasoningEffort = "no_think"
    enable_reasoning_effort: bool = False
    timeout_seconds: float = 120.0


def _normalize_reasoning_effort(value: str | None) -> ReasoningEffort:
    if value in {"no_think", "low", "high"}:
        return value
    return "no_think"


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Hy3Settings:
    load_dotenv()

    timeout = os.getenv("HY3_TIMEOUT_SECONDS", "120")
    try:
        timeout_seconds = float(timeout)
    except ValueError:
        timeout_seconds = 120.0

    return Hy3Settings(
        base_url=os.getenv("HY3_BASE_URL", Hy3Settings.base_url).rstrip("/"),
        api_key=os.getenv("HY3_API_KEY", Hy3Settings.api_key),
        model=os.getenv("HY3_MODEL", Hy3Settings.model),
        default_reasoning_effort=_normalize_reasoning_effort(
            os.getenv("HY3_DEFAULT_REASONING_EFFORT", Hy3Settings.default_reasoning_effort)
        ),
        enable_reasoning_effort=_parse_bool(
            os.getenv("HY3_ENABLE_REASONING_EFFORT"),
            default=Hy3Settings.enable_reasoning_effort,
        ),
        timeout_seconds=timeout_seconds,
    )
