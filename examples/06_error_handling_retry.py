"""
06_error_handling_retry.py

展示内容：
1. 网络超时重试
2. 429 指数退避
3. 401 / 400 / 5xx 的差异化处理
4. 成功后完整 response 解析

运行方式：
    pip install openai
    python examples/06_error_handling_retry.py

示例输出：
    Attempt 1 failed with timeout, retrying in 1.0s...
    Attempt 2 failed with 429, retrying in 2.0s...
    Success:
    Hy3 可以通过 OpenAI-compatible API 进行调用...
"""

from __future__ import annotations

import os
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)


BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")


def sleep_with_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 8.0) -> None:
    sleep_time = min(base_delay * (2 ** attempt), max_delay)
    print(f"Retrying in {sleep_time:.1f}s...")
    time.sleep(sleep_time)


def create_completion_with_retry(client: OpenAI, max_retries: int = 4):
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": "请简要说明如何通过 Hy3 的 OpenAI-compatible API 发起聊天请求。",
                    }
                ],
                temperature=0.3,
                top_p=1.0,
                max_tokens=256,
                timeout=30,
                extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
            )
        except AuthenticationError as exc:
            print("401 AuthenticationError: 请检查 HY3_API_KEY 或服务端鉴权配置。")
            raise exc
        except BadRequestError as exc:
            print("400 BadRequestError: 请检查 model、messages、tools、reasoning_effort 等参数。")
            if hasattr(exc, "body"):
                print(f"Error body: {exc.body}")
            raise exc
        except (APITimeoutError, APIConnectionError) as exc:
            if attempt >= max_retries:
                raise exc
            print(f"Attempt {attempt + 1} failed with network/timeout error: {type(exc).__name__}")
            sleep_with_backoff(attempt)
        except RateLimitError as exc:
            if attempt >= max_retries:
                raise exc
            print(f"Attempt {attempt + 1} failed with 429 rate limit: {exc}")
            sleep_with_backoff(attempt)
        except (InternalServerError, APIStatusError) as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code is not None and status_code < 500:
                raise exc
            if attempt >= max_retries:
                raise exc
            print(f"Attempt {attempt + 1} failed with server error: status={status_code}")
            sleep_with_backoff(attempt)

    raise RuntimeError("Unexpected retry exit.")


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    response = create_completion_with_retry(client)
    message = response.choices[0].message

    print("Success:")
    print(message.content or "")
    if response.usage:
        print(
            "Usage:",
            f"prompt={response.usage.prompt_tokens},",
            f"completion={response.usage.completion_tokens},",
            f"total={response.usage.total_tokens}",
        )


if __name__ == "__main__":
    main()
