"""Retry transient Hy3 API failures with bounded exponential backoff."""

import random
import sys
import time
from pathlib import Path
from typing import Any, Callable

from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import create_client, model_name, print_response  # noqa: E402


def retry_delay(error: Exception, attempt: int) -> float:
    """Honor Retry-After, otherwise use capped exponential backoff plus jitter."""
    response = getattr(error, "response", None)
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return min(float(retry_after), 30.0)
            except ValueError:
                pass
    return min(2 ** (attempt - 1), 30.0) + random.uniform(0.0, 0.25)


def is_retryable(error: Exception) -> bool:
    if isinstance(error, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    return isinstance(error, APIStatusError) and error.status_code >= 500


def call_with_retry(
    operation: Callable[[], Any],
    max_attempts: int = 5,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except (
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            APIStatusError,
        ) as exc:
            if not is_retryable(exc) or attempt == max_attempts:
                raise
            delay = retry_delay(exc, attempt)
            print(
                f"attempt {attempt}/{max_attempts} failed: {type(exc).__name__}; "
                f"retry in {delay:.2f}s"
            )
            sleep(delay)
    raise AssertionError("unreachable")


def main() -> None:
    # Disable SDK retries so this example owns the retry count and backoff policy.
    client = create_client(max_retries=0, timeout=20.0)

    def request() -> Any:
        return client.chat.completions.create(
            model=model_name(),
            messages=[{"role": "user", "content": "用一句话解释指数退避。"}],
            max_tokens=128,
        )

    response = call_with_retry(request)
    print_response(response)


if __name__ == "__main__":
    main()
