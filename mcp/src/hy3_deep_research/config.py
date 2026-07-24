"""Configuration management.

All settings are read from environment variables. No API key is ever hardcoded.
A missing required key raises a clear, actionable error.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    # --- Required ---
    hunyuan_api_key: str

    # --- Hy3 API (optional, with defaults) ---
    # TokenHub is the new unified platform (replaces the old api.hunyuan.cloud.tencent.com).
    hunyuan_base_url: str = "https://tokenhub.tencentmaas.com/v1"
    hunyuan_model: str = "hy3"
    # "top" (TokenHub cloud, default) or "template" (self-deployed vLLM/SGLang).
    reasoning_format: str = "top"

    # --- Search (external data source #1) ---
    search_max_results: int = 5
    tavily_api_key: str | None = None

    # --- Web fetch (external tool #2) ---
    fetch_max_chars: int = 8000
    fetch_timeout: int = 30

    # --- Deep research orchestration ---
    research_max_sub_queries: int = 3
    research_max_sources: int = 3
    research_reasoning_effort: str = "high"


class ConfigError(RuntimeError):
    """Raised when configuration is missing or invalid."""


def load_config() -> Config:
    """Build a Config from the current environment.

    Raises:
        ConfigError: if HUNYUAN_API_KEY is not set.
    """
    api_key = os.environ.get("HUNYUAN_API_KEY")
    if not api_key:
        raise ConfigError(
            "HUNYUAN_API_KEY environment variable is not set. "
            "Create a TokenHub API key at "
            "https://console.cloud.tencent.com/tokenhub and export it as "
            "HUNYUAN_API_KEY before starting the server."
        )

    reasoning_format = os.environ.get("HUNYUAN_REASONING_FORMAT", "top").strip().lower()
    if reasoning_format not in ("template", "top"):
        reasoning_format = "top"

    return Config(
        hunyuan_api_key=api_key,
        hunyuan_base_url=os.environ.get(
            "HUNYUAN_BASE_URL", "https://tokenhub.tencentmaas.com/v1"
        ),
        hunyuan_model=os.environ.get("HUNYUAN_MODEL", "hy3"),
        reasoning_format=reasoning_format,
        search_max_results=_get_int("SEARCH_MAX_RESULTS", 5),
        tavily_api_key=os.environ.get("TAVILY_API_KEY") or None,
        fetch_max_chars=_get_int("FETCH_MAX_CHARS", 8000),
        fetch_timeout=_get_int("FETCH_TIMEOUT", 30),
        research_max_sub_queries=_get_int("RESEARCH_MAX_SUB_QUERIES", 3),
        research_max_sources=_get_int("RESEARCH_MAX_SOURCES", 3),
        research_reasoning_effort=os.environ.get(
            "RESEARCH_REASONING_EFFORT", "high"
        ).strip().lower(),
    )
