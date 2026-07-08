from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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


def load_dotenv_file(path: Path) -> None:
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
        if key and not key.startswith("#"):
            os.environ.setdefault(key, _parse_env_value(raw_value))


def find_dotenv(start: Optional[Path] = None) -> Optional[Path]:
    explicit = os.getenv("HY3_ENV_FILE")
    if explicit:
        return Path(explicit).expanduser().resolve()

    current = (start or Path.cwd()).resolve()
    candidates = [current, *current.parents]
    for directory in candidates:
        env_file = directory / ".env"
        if env_file.exists():
            return env_file
    return None


def load_default_dotenv(start: Optional[Path] = None) -> Optional[Path]:
    env_file = find_dotenv(start)
    if env_file is None:
        return None
    load_dotenv_file(env_file)
    return env_file


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _api_key_for_base_url(base_url: str) -> str:
    hy3_key = os.getenv("HY3_API_KEY")
    if hy3_key and hy3_key != "EMPTY":
        return hy3_key
    if "openrouter.ai" in base_url:
        return os.getenv("OPENROUTER_API_KEY") or hy3_key or "EMPTY"
    if "hunyuan.cloud.tencent.com" in base_url:
        return os.getenv("HUNYUAN_API_KEY") or hy3_key or "EMPTY"
    return hy3_key or "EMPTY"


@dataclass(frozen=True)
class Hy3Settings:
    base_url: str
    api_key: str
    model: str
    temperature: float
    top_p: float
    max_tokens: int
    reasoning_effort: str

    @classmethod
    def from_env(cls) -> "Hy3Settings":
        base_url = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
        return cls(
            base_url=base_url,
            api_key=_api_key_for_base_url(base_url),
            model=os.getenv("HY3_MODEL", "hy3"),
            temperature=_float_env("HY3_TEMPERATURE", 0.9),
            top_p=_float_env("HY3_TOP_P", 1.0),
            max_tokens=_int_env("HY3_MAX_TOKENS", 2048),
            reasoning_effort=os.getenv("HY3_REASONING_EFFORT", "high"),
        )


@dataclass(frozen=True)
class ResearchSettings:
    """Web data source settings. No key is required for the built-in search."""

    search_api_key: Optional[str]
    search_engine: str
    max_search_results: int
    page_timeout: float
    max_page_chars: int
    user_agent: str

    @classmethod
    def from_env(cls) -> "ResearchSettings":
        return cls(
            search_api_key=os.getenv("HY3_SEARCH_API_KEY")
            or os.getenv("TAVILY_API_KEY")
            or os.getenv("BRAVE_API_KEY"),
            search_engine=os.getenv("HY3_SEARCH_ENGINE", "duckduckgo"),
            max_search_results=_int_env("HY3_MAX_SEARCH_RESULTS", 5),
            page_timeout=_float_env("HY3_PAGE_TIMEOUT", 15.0),
            max_page_chars=_int_env("HY3_MAX_PAGE_CHARS", 8000),
            user_agent=os.getenv(
                "HY3_USER_AGENT",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            ),
        )