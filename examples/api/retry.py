#!/usr/bin/env python3
"""Hy3 error handling and retry example with exponential backoff.

Environment:
  HY3_BASE_URL=http://127.0.0.1:8000/v1
  HY3_API_KEY=EMPTY
  HY3_MODEL=hy3
  HY3_TIMEOUT=30
  HY3_RETRY_MAX_ATTEMPTS=5

Run:
  python3 examples/api/retry.py

Sample output:
  attempt=1 status=retryable error=RateLimitError sleep_s=0.64
  attempt=2 status=success
  content: ...
"""

from __future__ import annotations

import os
import random
import time
from collections.abc import Callable
from typing import TypeVar

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from common import MODEL, make_client, print_json, print_runtime_config, request_options


TIMEOUT = float(os.getenv("HY3_TIMEOUT", "30"))
MAX_ATTEMPTS = int(os.getenv("HY3_RETRY_MAX_ATTEMPTS", "5"))

T = TypeVar("T")

PERMANENT_ERRORS = (
    BadRequestError,
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
)
RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


def is_retryable(exc: Exception) -> bool:
    if isinstance(exc, PERMANENT_ERRORS):
        return False
    if isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in RETRYABLE_STATUS_CODES
    return False


def backoff_seconds(attempt: int) -> float:
    base = min(8.0, 0.5 * (2 ** (attempt - 1)))
    jitter = random.uniform(0.0, 0.25)
    return base + jitter


def call_with_retry(operation: Callable[[], T], max_attempts: int = MAX_ATTEMPTS) -> T:
    for attempt in range(1, max_attempts + 1):
        try:
            result = operation()
            print(f"attempt={attempt} status=success")
            return result
        except Exception as exc:
            retryable = is_retryable(exc)
            if not retryable or attempt == max_attempts:
                print(
                    "attempt={attempt} status=failed retryable={retryable} "
                    "error_type={error_type} error={error}".format(
                        attempt=attempt,
                        retryable=retryable,
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                )
                raise

            sleep_s = backoff_seconds(attempt)
            status_code = getattr(exc, "status_code", None)
            print(
                "attempt={attempt} status=retryable status_code={status_code} "
                "error_type={error_type} sleep_s={sleep_s:.2f}".format(
                    attempt=attempt,
                    status_code=status_code,
                    error_type=type(exc).__name__,
                    sleep_s=sleep_s,
                )
            )
            time.sleep(sleep_s)

    raise RuntimeError("retry loop exited unexpectedly")


def main() -> None:
    print_runtime_config()
    client = make_client(timeout=TIMEOUT)

    request = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "Give a compact checklist for retrying Hy3 API requests safely.",
            }
        ],
        "temperature": 0.3,
        "top_p": 1.0,
        "max_tokens": 256,
        **request_options(reasoning_effort="no_think"),
    }
    print_json("retry request", request)

    response = call_with_retry(lambda: client.chat.completions.create(**request))
    choice = response.choices[0]
    message = choice.message

    print("\n=== parsed response ===")
    print("id:", response.id)
    print("model:", response.model)
    print("finish_reason:", choice.finish_reason)
    print("content:", message.content)
    if response.usage:
        print_json("usage", response.usage)


if __name__ == "__main__":
    main()
