"""Bounded retry handling for Hy3 timeouts, rate limits, and server errors."""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

from common import create_client, load_config, usage_dict

RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


def is_retryable(exc: Exception) -> bool:
    """Return true only for transient transport, limit, or server failures."""

    if isinstance(
        exc,
        (APITimeoutError, APIConnectionError, RateLimitError, InternalServerError),
    ):
        return True
    return getattr(exc, "status_code", None) in RETRYABLE_STATUS_CODES


def retry_after_seconds(
    exc: Exception,
    *,
    now: datetime | None = None,
) -> float | None:
    """Parse Retry-After as seconds or an HTTP date."""

    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(str(raw))
        except (TypeError, ValueError, OverflowError):
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        current = now or datetime.now(timezone.utc)
        return max(0.0, (retry_at - current).total_seconds())


def backoff_seconds(
    attempt: int,
    *,
    retry_after: float | None,
    base_delay: float,
    max_delay: float,
    random_value: float,
) -> float:
    """Honor Retry-After, otherwise return exponential backoff with jitter."""

    if retry_after is not None:
        return retry_after
    exponential = min(max_delay, base_delay * (2 ** (attempt - 1)))
    return min(max_delay, exponential + exponential * 0.25 * random_value)


def request_with_retry(
    client: Any,
    request: dict[str, Any],
    *,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
    random_value: Callable[[], float] = random.random,
) -> Any:
    """Send a request with a finite retry budget.

    A Retry-After value larger than `max_delay` is not shortened; the function
    stops and lets the caller decide when to retry again.
    """

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(**request)
        except Exception as exc:
            if not is_retryable(exc) or attempt == max_attempts:
                raise

            retry_after = retry_after_seconds(exc)
            delay = backoff_seconds(
                attempt,
                retry_after=retry_after,
                base_delay=base_delay,
                max_delay=max_delay,
                random_value=random_value(),
            )
            if delay > max_delay:
                print(
                    f"Retry-After={delay:.1f}s exceeds the {max_delay:.1f}s "
                    "example wait budget; stopping."
                )
                raise

            status = getattr(exc, "status_code", None)
            request_id = getattr(exc, "request_id", None)
            print(
                f"attempt {attempt}/{max_attempts} failed: "
                f"{type(exc).__name__}, status={status}, request_id={request_id}; "
                f"retrying in {delay:.2f}s"
            )
            sleep(delay)

    raise AssertionError("unreachable")


def main() -> None:
    config = load_config()
    # Disable SDK retries so this example has exactly one visible retry policy.
    client = create_client(config, timeout=30.0, max_retries=0)
    request = {
        "model": config.model,
        "messages": [
            {"role": "user", "content": "用一句话说明为什么重试需要随机抖动。"}
        ],
        "temperature": 0.2,
        "max_tokens": 256,
        "extra_body": {"thinking": {"type": "disabled"}},
    }

    try:
        response = request_with_retry(client, request)
    except Exception as exc:
        print("request failed permanently:", type(exc).__name__, str(exc))
        raise SystemExit(1) from exc

    choice = response.choices[0]
    print("id:", response.id, "model:", response.model)
    print("assistant:", choice.message.content)
    print("finish_reason:", choice.finish_reason)
    print("usage:", usage_dict(response))


if __name__ == "__main__":
    main()
