"""Shared .env-backed configuration for the OpenAI-compatible examples."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

# Hy3 responses may contain Unicode characters that Windows' GBK console cannot print.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROVIDER = os.getenv("API_PROVIDER", "hy3").strip().lower()
if PROVIDER not in {"hy3", "hunyuan"}:
    raise ValueError("API_PROVIDER must be either 'hy3' or 'hunyuan'")

if PROVIDER == "hunyuan":
    BASE_URL = os.getenv("HUNYUAN_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1")
    API_KEY = os.getenv("HUNYUAN_API_KEY", "")
    MODEL = os.getenv("HUNYUAN_MODEL", "hunyuan-turbos-latest")
else:
    BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
    API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
    MODEL = os.getenv("HY3_MODEL", "hy3")

TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "4"))
RETRY_BASE_DELAY_SECONDS = float(os.getenv("RETRY_BASE_DELAY_SECONDS", "1"))
RETRY_MAX_DELAY_SECONDS = float(os.getenv("RETRY_MAX_DELAY_SECONDS", "8"))


def build_client() -> OpenAI:
    """Create an OpenAI SDK client for the provider selected in .env."""
    if PROVIDER == "hunyuan" and (
        not API_KEY or API_KEY == "your-hunyuan-api-key-here"
    ):
        raise RuntimeError(
            "HUNYUAN_API_KEY is not configured. Copy .env.example to .env and set it."
        )
    return OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=TIMEOUT_SECONDS)


def reasoning_extra_body(reasoning_effort: str) -> dict[str, object]:
    """Return Hy3's reasoning switch; Hunyuan does not need this Hy3-only field."""
    if PROVIDER != "hy3":
        return {}
    return {"chat_template_kwargs": {"reasoning_effort": reasoning_effort}}
