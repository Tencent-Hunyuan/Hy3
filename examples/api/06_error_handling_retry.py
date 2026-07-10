"""演示可控的 API 错误重试与退避策略。"""

from __future__ import annotations

import argparse
import random
import time
from typing import Callable, Iterator, TypeVar

import httpx
from openai import APIConnectionError, APITimeoutError, RateLimitError

from common import (
    Hy3Config,
    create_client,
    print_json,
    reasoning_extra_body,
    summarize_completion,
)


T = TypeVar("T")
RetryCallback = Callable[[int, int, float, Exception], None]


def is_retryable(error: Exception) -> bool:
    """判断错误是否适合由应用层执行有限重试。"""
    if isinstance(error, (APIConnectionError, APITimeoutError)):
        return True

    response = getattr(error, "response", None)
    status_code = getattr(response, "status_code", None)
    return isinstance(status_code, int) and (
        status_code in (408, 409, 429) or status_code >= 500
    )


def retry_after_seconds(error: Exception) -> float | None:
    """读取有效的 Retry-After 秒数。"""
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return None

    try:
        retry_after = float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None
    return retry_after if retry_after >= 0 else None


def call_with_retry(
    operation: Callable[[], T],
    *,
    max_attempts: int = 4,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
    sleep: Callable[[float], None] = time.sleep,
    random_value: Callable[[], float] = random.random,
    on_retry: RetryCallback | None = None,
) -> T:
    """以有限指数退避和 full jitter 执行操作。"""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if base_delay < 0:
        raise ValueError("base_delay must be non-negative")
    if max_delay <= 0:
        raise ValueError("max_delay must be positive")

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except Exception as error:
            if not is_retryable(error) or attempt == max_attempts:
                raise

            delay = retry_after_seconds(error)
            if delay is None:
                delay_limit = min(
                    max_delay,
                    base_delay * 2 ** (attempt - 1),
                )
                delay = random_value() * delay_limit

            next_attempt = attempt + 1
            if on_retry is not None:
                on_retry(next_attempt, max_attempts, delay, error)
            sleep(delay)

    raise RuntimeError("unreachable")


def recovery_operation(errors: Iterator[Exception]) -> Callable[[], str]:
    """创建依次抛出模拟错误、最终恢复的操作。"""

    def operation() -> str:
        try:
            error = next(errors)
        except StopIteration:
            return "recovered"
        raise error

    return operation


def print_retry(
    next_attempt: int,
    max_attempts: int,
    delay: float,
    error: Exception,
) -> None:
    """打印不包含敏感配置的重试进度。"""
    print(
        f"Retry {next_attempt}/{max_attempts} in {delay:.2f}s "
        f"after {type(error).__name__}"
    )


def run_simulation() -> None:
    """运行不依赖 API 配置或网络的恢复演示。"""
    request = httpx.Request(
        "POST",
        "https://example.invalid/v1/chat/completions",
    )
    rate_limit_response = httpx.Response(
        429,
        request=request,
        headers={"Retry-After": "0"},
    )
    scenarios = (
        (
            "rate_limit",
            RateLimitError(
                "simulated rate limit",
                response=rate_limit_response,
                body=None,
            ),
        ),
        ("timeout", APITimeoutError(request)),
        ("connection", APIConnectionError(request=request)),
    )

    for label, error in scenarios:
        result = call_with_retry(
            recovery_operation(iter((error,))),
            sleep=lambda _: None,
            random_value=lambda: 0.0,
            on_retry=print_retry,
        )
        print(f"{label}: {result}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run retry scenarios without API configuration.",
    )
    args = parser.parse_args()
    if args.simulate:
        run_simulation()
        return

    config = Hy3Config.from_env()
    client = create_client(config, max_retries=0)
    response = call_with_retry(
        lambda: client.chat.completions.create(
            model=config.model,
            messages=[
                {
                    "role": "user",
                    "content": "Give one sentence about reliable API clients.",
                }
            ],
            temperature=0.9,
            top_p=1.0,
            max_tokens=128,
            extra_body=reasoning_extra_body(config, "no_think"),
        ),
        on_retry=print_retry,
    )
    print_json("Retry response", summarize_completion(response))


if __name__ == "__main__":
    main()
