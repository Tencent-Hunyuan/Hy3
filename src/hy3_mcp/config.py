"""Environment-driven configuration for the Hy3 KB MCP server.

All secrets (API keys) are loaded exclusively from the environment. Nothing is
hardcoded here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings resolved from environment variables."""

    api_key: str
    base_url: str
    model: str
    # Where the persisted knowledge-base index is stored (JSON file).
    kb_store_path: str
    # Maximum number of tokens-ish characters sent to the model as context.
    max_context_chars: int

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def load_settings() -> Settings:
    """Load settings from the environment.

    Required:
        HY3_API_KEY         Hy3 / Tencent TokenHub API key.

    Optional (with sensible defaults):
        HY3_BASE_URL        Defaults to https://tokenhub.tencentmaas.com/v1
        HY3_MODEL           Defaults to "hy3"
        HY3_KB_STORE        Persisted index path; defaults to ".hy3_kb_store.json"
                            in the current working directory.
        HY3_MAX_CONTEXT_CHARS  Max chars of retrieved chunks fed to the model.
    """
    api_key = os.environ.get("HY3_API_KEY", "").strip()
    base_url = os.environ.get(
        "HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"
    ).strip()
    model = os.environ.get("HY3_MODEL", "hy3").strip()
    kb_store_path = os.environ.get(
        "HY3_KB_STORE", os.path.join(os.getcwd(), ".hy3_kb_store.json")
    ).strip()
    try:
        max_context_chars = int(
            os.environ.get("HY3_MAX_CONTEXT_CHARS", "12000").strip()
        )
    except ValueError:
        max_context_chars = 12000

    return Settings(
        api_key=api_key,
        base_url=base_url,
        model=model,
        kb_store_path=kb_store_path,
        max_context_chars=max_context_chars,
    )
