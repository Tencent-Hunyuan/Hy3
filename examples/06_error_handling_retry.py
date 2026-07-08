"""Hy3 example 06: error handling and retry."""

import os
import random
import time
from typing import Iterable

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=30.0, max_retries=0)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def sleep_with_backoff(attempt: int, base: float = 0.8, cap: float = 8.0) -> None:
    delay = min(cap, base * (2 ** attempt))
    delay = delay * (0.5 + random.random())
    print(f"retrying in {delay:.2f}s...")
    time.sleep(delay)


def should_retry_status(exc: APIStatusError) -> bool:
    return exc.status_code in RETRYABLE_STATUS_CODES


def create_chat_with_retry(messages: Iterable[dict], max_attempts: int = 5):
    last_error = None
    for attempt in range(max_attempts):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=list(messages),
                temperature=0.3,
                max_tokens=512,
                extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
            )
        except RateLimitError as exc:
            last_error = exc
            print(f"attempt {attempt + 1}: rate limited")
        except (APITimeoutError, APIConnectionError) as exc:
            last_error = exc
            print(f"attempt {attempt + 1}: network/timeout error: {type(exc).__name__}")
        except APIStatusError as exc:
            last_error = exc
            print(f"attempt {attempt + 1}: HTTP {exc.status_code}: {exc.message}")
            if not should_retry_status(exc):
                raise

        if attempt == max_attempts - 1:
            break
        sleep_with_backoff(attempt)

    raise RuntimeError(f"request failed after {max_attempts} attempts") from last_error


if __name__ == "__main__":
    response = create_chat_with_retry(
        [{"role": "user", "content": "请用三点说明 API 请求重试为什么需要退避和抖动。"}]
    )
    print(response.choices[0].message.content)
    print("usage:", response.usage)
