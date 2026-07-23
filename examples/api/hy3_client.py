"""Small, tested helpers shared by the runnable Hy3 API examples.

The module deliberately contains transport concerns only. Each numbered example
keeps its own request and response handling visible so readers can understand it
without learning a framework first.
"""

from __future__ import annotations

import os
import random
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, TypeVar
from urllib.parse import urlsplit

from dotenv import load_dotenv
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_MODEL = "hy3"
RETRYABLE_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})
REASONING_EFFORTS = frozenset({"no_think", "low", "high"})

T = TypeVar("T")
_MISSING = object()


@dataclass(frozen=True)
class Hy3Config:
    """Connection settings loaded from environment variables."""

    base_url: str = DEFAULT_BASE_URL
    api_key: str = "EMPTY"
    model: str = DEFAULT_MODEL
    timeout: float = 120.0

    @classmethod
    def from_env(cls) -> Hy3Config:
        """Load a nearby ``.env`` file, then read and validate settings."""

        load_dotenv()
        raw_timeout = os.getenv("HY3_TIMEOUT", "120")
        try:
            timeout = float(raw_timeout)
        except ValueError as error:
            raise ValueError("HY3_TIMEOUT must be a number of seconds") from error

        config = cls(
            base_url=os.getenv("HY3_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            api_key=os.getenv("HY3_API_KEY", "EMPTY"),
            model=os.getenv("HY3_MODEL", DEFAULT_MODEL),
            timeout=timeout,
        )
        config.validate()
        return config

    def validate(self) -> None:
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("HY3_BASE_URL must be an absolute http(s) URL")
        if parsed.username or parsed.password:
            raise ValueError("HY3_BASE_URL must not contain credentials")
        if self.timeout <= 0:
            raise ValueError("HY3_TIMEOUT must be greater than zero")
        if not self.api_key:
            raise ValueError("HY3_API_KEY must be non-empty; use EMPTY for a local server")
        if not self.model:
            raise ValueError("HY3_MODEL must be non-empty")

    def safe_summary(self) -> str:
        """Describe the target without printing credentials."""

        return f"base_url={self.base_url} model={self.model} timeout={self.timeout:g}s"


def create_client(config: Hy3Config) -> OpenAI:
    """Create an OpenAI client with SDK retries disabled for predictable demos."""

    return OpenAI(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
        max_retries=0,
    )


def reasoning_options(effort: str) -> dict[str, Any]:
    """Return Hy3's chat-template extension for one reasoning level."""

    if effort not in REASONING_EFFORTS:
        choices = ", ".join(sorted(REASONING_EFFORTS))
        raise ValueError(f"reasoning effort must be one of: {choices}")
    return {"chat_template_kwargs": {"reasoning_effort": effort}}


def value_from(payload: Any, field: str, default: Any = None) -> Any:
    """Read a field from SDK models, dictionaries, or ``model_extra``."""

    if isinstance(payload, Mapping):
        return payload.get(field, default)
    value = getattr(payload, field, _MISSING)
    if value is not _MISSING:
        return value
    model_extra = getattr(payload, "model_extra", None)
    if isinstance(model_extra, Mapping):
        return model_extra.get(field, default)
    return default


def split_message(message: Any) -> tuple[str, str]:
    """Return ``(reasoning_content, final_content)`` with empty values normalized."""

    reasoning = value_from(message, "reasoning_content", "") or ""
    content = value_from(message, "content", "") or ""
    return str(reasoning), str(content)


def stream_fragments(chunks: Iterable[Any]) -> Iterable[tuple[str, str]]:
    """Yield ``(reasoning_delta, content_delta)`` from non-empty stream chunks."""

    for chunk in chunks:
        choices = value_from(chunk, "choices", []) or []
        if not choices:
            continue
        delta = value_from(choices[0], "delta")
        if delta is None:
            continue
        reasoning = value_from(delta, "reasoning_content", "") or ""
        content = value_from(delta, "content", "") or ""
        if reasoning or content:
            yield str(reasoning), str(content)


def retry_after_seconds(error: BaseException, now: float | None = None) -> float | None:
    """Read a numeric or HTTP-date ``Retry-After`` value from an SDK error."""

    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if not headers or not hasattr(headers, "get"):
        return None
    value = headers.get("retry-after") or headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        pass
    try:
        parsed = parsedate_to_datetime(str(value))
        return max(0.0, parsed.timestamp() - (time.time() if now is None else now))
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def is_retryable(error: BaseException) -> bool:
    """Return whether retrying this client/API failure is normally safe."""

    if isinstance(error, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(error, APIStatusError):
        return getattr(error, "status_code", None) in RETRYABLE_STATUS_CODES
    status_code = getattr(error, "status_code", None)
    return status_code in RETRYABLE_STATUS_CODES


def call_with_retry(
    operation: Callable[[], T],
    *,
    attempts: int = 4,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    sleep: Callable[[float], None] = time.sleep,
    random_value: Callable[[], float] = random.random,
    on_retry: Callable[[int, float, BaseException], None] | None = None,
) -> T:
    """Run an operation with capped exponential backoff and full jitter."""

    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    if base_delay < 0 or max_delay < 0:
        raise ValueError("retry delays must be non-negative")

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as error:
            if not is_retryable(error) or attempt == attempts:
                raise
            cap = min(max_delay, base_delay * (2 ** (attempt - 1)))
            server_delay = retry_after_seconds(error)
            delay = max(cap * random_value(), server_delay or 0.0)
            if on_retry:
                on_retry(attempt, delay, error)
            sleep(delay)

    raise AssertionError("unreachable")
