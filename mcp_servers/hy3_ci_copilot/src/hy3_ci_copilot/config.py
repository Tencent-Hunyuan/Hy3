from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from urllib.parse import urlparse

from hy3_ci_copilot.errors import ConfigurationError

APIStyle = Literal["auto", "native", "openrouter"]


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}.") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number, got {raw!r}.") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}.")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    api_style: APIStyle
    allowed_roots: tuple[Path, ...]
    timeout_seconds: float
    max_input_chars: int
    max_output_tokens: int
    max_retries: int

    def __post_init__(self) -> None:
        if not self.api_key.isascii() or any(
            ord(character) < 0x20 or ord(character) == 0x7F for character in self.api_key
        ):
            raise ConfigurationError(
                "HY3_API_KEY must contain only ASCII characters valid in an HTTP header."
            )

    @classmethod
    def from_env(cls) -> Settings:
        api_key = os.getenv("HY3_API_KEY", "").strip()
        if not api_key:
            raise ConfigurationError(
                "HY3_API_KEY is required. Use EMPTY for a local endpoint without authentication."
            )

        base_url = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1").strip().rstrip("/")
        parsed_url = urlparse(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ConfigurationError("HY3_BASE_URL must be an absolute http:// or https:// URL.")
        if parsed_url.username or parsed_url.password or parsed_url.query or parsed_url.fragment:
            raise ConfigurationError(
                "HY3_BASE_URL cannot contain credentials, query parameters, or fragments."
            )

        model = os.getenv("HY3_MODEL", "hy3").strip()
        if not model:
            raise ConfigurationError("HY3_MODEL cannot be empty.")

        raw_style = os.getenv("HY3_API_STYLE", "auto").strip().lower()
        if raw_style not in {"auto", "native", "openrouter"}:
            raise ConfigurationError("HY3_API_STYLE must be auto, native, or openrouter.")
        api_style = cast(APIStyle, raw_style)

        raw_roots = os.getenv("HY3_ALLOWED_ROOTS", "")
        root_values = [item.strip() for item in raw_roots.split(os.pathsep) if item.strip()]
        if not root_values:
            root_values = [str(Path.cwd())]
        allowed_roots = tuple(Path(item).expanduser().resolve() for item in root_values)
        missing_roots = [str(root) for root in allowed_roots if not root.is_dir()]
        if missing_roots:
            raise ConfigurationError(
                "HY3_ALLOWED_ROOTS contains missing directories: " + ", ".join(missing_roots)
            )

        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            api_style=api_style,
            allowed_roots=allowed_roots,
            timeout_seconds=_bounded_float("HY3_TIMEOUT_SECONDS", 120, 1, 600),
            max_input_chars=_bounded_int("HY3_MAX_INPUT_CHARS", 120_000, 10_000, 1_000_000),
            max_output_tokens=_bounded_int("HY3_MAX_OUTPUT_TOKENS", 4096, 256, 32_768),
            max_retries=_bounded_int("HY3_MAX_RETRIES", 2, 0, 5),
        )

    @property
    def resolved_api_style(self) -> Literal["native", "openrouter"]:
        if self.api_style != "auto":
            return self.api_style
        hostname = (urlparse(self.base_url).hostname or "").lower()
        return "openrouter" if hostname == "openrouter.ai" else "native"
