"""OpenAI-compatible Hy3 client creation and bounded retry helpers."""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlparse

from .config import Settings

RetryCallback = Callable[[Exception, int, float], None]


def create_client(settings: Settings) -> Any:
    """Create an OpenAI SDK client while keeping the SDK an optional import."""

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - depends on local installation
        raise RuntimeError(
            "The OpenAI Python SDK is required; install the example requirements"
        ) from exc

    # Agent-level retries own the attempt count and emit observable retry events.
    return OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout=settings.timeout,
        max_retries=0,
    )


create_hy3_client = create_client


def reasoning_body(settings: Settings) -> dict[str, Any]:
    """Use the provider's supported reasoning control without changing call sites."""
    hostname = (urlparse(settings.base_url).hostname or "").casefold()
    if hostname == "openrouter.ai" or hostname.endswith(".openrouter.ai"):
        effort = "minimal" if settings.reasoning_effort == "no_think" else settings.reasoning_effort
        return {"reasoning": {"effort": effort}}
    return {
        "chat_template_kwargs": {
            "reasoning_effort": settings.reasoning_effort,
        }
    }


def _status_code(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    if isinstance(status, int):
        return status
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def is_retryable(error: Exception) -> bool:
    """Return whether an API failure is likely to succeed on a later attempt."""

    status = _status_code(error)
    if status is not None:
        return status in {408, 429} or 500 <= status <= 599
    if isinstance(error, (ConnectionError, TimeoutError)):
        return True
    return type(error).__name__ in {
        "APIConnectionError",
        "APITimeoutError",
        "ConnectError",
        "ConnectTimeout",
        "PoolTimeout",
        "RateLimitError",
        "ReadTimeout",
        "WriteTimeout",
    }


def _retry_after(error: Exception) -> float | None:
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if not isinstance(headers, Mapping) and not hasattr(headers, "get"):
        return None
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return None


def retry_delay(
    error: Exception,
    attempt: int,
    *,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    jitter: Callable[[float, float], float] | None = None,
) -> float:
    """Honor Retry-After or calculate capped exponential backoff with jitter."""

    server_delay = _retry_after(error)
    if server_delay is not None:
        return min(server_delay, max_delay)
    exponential = min(base_delay * (2 ** max(0, attempt - 1)), max_delay)
    jitter_fn = random.uniform if jitter is None else jitter
    return min(exponential + jitter_fn(0.0, exponential * 0.25), max_delay)


def call_with_retry(
    operation: Callable[[], Any],
    *,
    max_attempts: int,
    base_delay: float,
    max_delay: float,
    sleep: Callable[[float], None] = time.sleep,
    on_retry: RetryCallback | None = None,
) -> Any:
    """Execute an operation and retry only transient failures."""

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == max_attempts or not is_retryable(exc):
                raise
            delay = retry_delay(
                exc,
                attempt,
                base_delay=base_delay,
                max_delay=max_delay,
            )
            if on_retry is not None:
                on_retry(exc, attempt, delay)
            sleep(delay)
    raise AssertionError("unreachable")


def create_chat_completion(
    client: Any,
    settings: Settings,
    messages: Sequence[Mapping[str, Any]],
    tools: Sequence[Mapping[str, Any]] | None = None,
    *,
    on_retry: RetryCallback | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """Send one non-streaming Hy3 chat request through an OpenAI-style client."""

    request: dict[str, Any] = {
        "model": settings.model,
        "messages": list(messages),
        "max_tokens": settings.max_tokens,
        "temperature": settings.temperature,
        "top_p": settings.top_p,
        "extra_body": reasoning_body(settings),
    }
    if tools:
        request["tools"] = list(tools)
        request["tool_choice"] = "auto"

    return call_with_retry(
        lambda: client.chat.completions.create(**request),
        max_attempts=settings.max_attempts,
        base_delay=settings.retry_base_delay,
        max_delay=settings.retry_max_delay,
        sleep=sleep,
        on_retry=on_retry,
    )
