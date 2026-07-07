"""Shared configuration helpers for Hy3 OpenAI-compatible API examples."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"


def _strip_inline_comment(value: str) -> str:
    in_single = False
    in_double = False
    escaped = False

    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "#" and not in_single and not in_double:
            if index == 0 or value[index - 1].isspace():
                return value[:index].rstrip()
    return value.strip()


def _parse_env_value(raw_value: str) -> str:
    value = _strip_inline_comment(raw_value.strip())
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value


def load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key.startswith("#"):
            continue
        os.environ.setdefault(key, _parse_env_value(raw_value))


load_dotenv()

PROVIDER = os.getenv("HY3_PROVIDER", "local").strip().lower()


def _env_first(*names: str, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


def _cloud_key(name: str) -> Optional[str]:
    value = os.getenv(name)
    if not value or value == "EMPTY":
        return None
    return value


def default_base_url() -> str:
    if PROVIDER == "openrouter":
        return "https://openrouter.ai/api/v1"
    if PROVIDER in {"tencent", "tencent-hunyuan", "hunyuan"}:
        return "https://api.hunyuan.cloud.tencent.com/v1"
    return "http://127.0.0.1:8000/v1"


def default_model() -> str:
    if PROVIDER in {"tencent", "tencent-hunyuan", "hunyuan"}:
        return "hunyuan-turbos-latest"
    return "hy3"


def default_api_key() -> str:
    if PROVIDER == "openrouter":
        return _cloud_key("OPENROUTER_API_KEY") or _cloud_key("HY3_API_KEY") or "EMPTY"
    if PROVIDER in {"tencent", "tencent-hunyuan", "hunyuan"}:
        return _cloud_key("HUNYUAN_API_KEY") or _cloud_key("HY3_API_KEY") or "EMPTY"
    return _env_first("HY3_API_KEY", default="EMPTY") or "EMPTY"


BASE_URL = _env_first("HY3_BASE_URL", default=default_base_url()) or default_base_url()
API_KEY = default_api_key()
MODEL = _env_first("HY3_MODEL", default=default_model()) or default_model()


def default_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if PROVIDER == "openrouter":
        referer = os.getenv("OPENROUTER_HTTP_REFERER")
        app_title = os.getenv("OPENROUTER_APP_TITLE")
        if referer:
            headers["HTTP-Referer"] = referer
        if app_title:
            headers["X-OpenRouter-Title"] = app_title
    return headers


def make_client(timeout: Optional[float] = None) -> Any:
    from openai import OpenAI

    kwargs: Dict[str, Any] = {
        "base_url": BASE_URL,
        "api_key": API_KEY,
    }
    headers = default_headers()
    if headers:
        kwargs["default_headers"] = headers
    if timeout is not None:
        kwargs["timeout"] = timeout
    return OpenAI(**kwargs)


def _send_hy3_reasoning_by_default() -> bool:
    return PROVIDER in {"local", "vllm", "sglang", "hy3", "self-hosted", "selfhosted"}


def should_send_hy3_reasoning() -> bool:
    value = os.getenv("HY3_SEND_REASONING", "auto").strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return _send_hy3_reasoning_by_default()


def user_extra_body() -> Dict[str, Any]:
    raw = os.getenv("HY3_EXTRA_BODY_JSON")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"HY3_EXTRA_BODY_JSON is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("HY3_EXTRA_BODY_JSON must decode to a JSON object")
    return parsed


def _openrouter_reasoning(reasoning_effort: str) -> Dict[str, str]:
    effort_map = {
        "no_think": "none",
        "low": "low",
        "high": "high",
    }
    return {"effort": effort_map.get(reasoning_effort, reasoning_effort)}


def request_options(reasoning_effort: Optional[str] = "no_think") -> Dict[str, Any]:
    extra_body = user_extra_body()
    if reasoning_effort and PROVIDER == "openrouter" and "reasoning" not in extra_body:
        extra_body["reasoning"] = _openrouter_reasoning(reasoning_effort)
    elif reasoning_effort and should_send_hy3_reasoning():
        chat_template_kwargs = dict(extra_body.get("chat_template_kwargs", {}))
        chat_template_kwargs["reasoning_effort"] = reasoning_effort
        extra_body["chat_template_kwargs"] = chat_template_kwargs
    return {"extra_body": extra_body} if extra_body else {}


def to_plain(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    if isinstance(value, tuple):
        return [to_plain(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return to_plain(value.model_dump())
    if hasattr(value, "dict"):
        return to_plain(value.dict())
    return value


def print_json(title: str, value: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(to_plain(value), ensure_ascii=False, indent=2))


def print_runtime_config() -> None:
    print_json(
        "runtime config",
        {
            "provider": PROVIDER,
            "base_url": BASE_URL,
            "model": MODEL,
            "api_key_source": "configured" if API_KEY != "EMPTY" else "EMPTY",
            "send_hy3_reasoning": should_send_hy3_reasoning(),
            "default_headers": default_headers(),
            "user_extra_body": user_extra_body(),
            "dotenv": str(ENV_FILE) if ENV_FILE.exists() else None,
        },
    )
