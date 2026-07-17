"""Hy3 API 超时、限流、网络错误与服务端错误的重试示例。"""

import os
import random
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)


def load_project_env() -> None:
    candidates = [Path.cwd() / ".env", Path.cwd() / "quickstart" / ".env"]
    if "__file__" in globals():
        candidates.insert(0, Path(__file__).resolve().parents[2] / ".env")
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


load_project_env()

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")
TIMEOUT_SECONDS = float(os.getenv("HY3_TIMEOUT_SECONDS", "30"))
MAX_RETRIES = int(os.getenv("HY3_MAX_RETRIES", "3"))
RETRY_BASE_SECONDS = float(os.getenv("HY3_RETRY_BASE_SECONDS", "1"))
RETRY_MAX_SECONDS = float(os.getenv("HY3_RETRY_MAX_SECONDS", "30"))


def retry_after_seconds(exc) -> float | None:
    """读取限流响应中的 Retry-After 秒数；非数字格式交给指数退避。"""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    value = response.headers.get("retry-after")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def retry_category(exc) -> str | None:
    if isinstance(exc, RateLimitError):
        return "限流"
    if isinstance(exc, APITimeoutError):
        return "超时"
    if isinstance(exc, APIConnectionError):
        return "网络错误"
    if isinstance(exc, APIStatusError) and exc.status_code >= 500:
        return f"服务端错误 HTTP {exc.status_code}"
    return None


def compute_delay(retry_index: int, exc) -> float:
    retry_after = retry_after_seconds(exc)
    if retry_after is not None:
        return min(RETRY_MAX_SECONDS, retry_after)
    exponential = min(RETRY_MAX_SECONDS, RETRY_BASE_SECONDS * (2**retry_index))
    jitter = random.uniform(0.0, min(1.0, exponential * 0.1))
    return min(RETRY_MAX_SECONDS, exponential + jitter)


def create_completion_with_retry(client: OpenAI):
    """最多执行 1 + MAX_RETRIES 次请求，并只重试暂时性错误。"""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": "请用一句话解释什么是指数退避。",
                    }
                ],
                temperature=0.9,
                top_p=1.0,
                max_tokens=128,
                extra_body={
                    "chat_template_kwargs": {
                        "reasoning_effort": "no_think",
                    }
                },
            )
        except (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError) as exc:
            category = retry_category(exc)
            if category is None:
                # 400/401/403/404 等通常不是短暂故障，立即交给调用方处理。
                raise
            if attempt >= MAX_RETRIES:
                print(f"{category}：已用尽 {MAX_RETRIES} 次重试")
                raise

            delay = compute_delay(attempt, exc)
            print(
                f"第 {attempt + 1} 次请求失败（{category}），"
                f"{delay:.2f}s 后进行第 {attempt + 1} 次重试"
            )
            time.sleep(delay)

    raise RuntimeError("不可达分支")


def parse_response(response) -> None:
    print("\n=== 请求成功 ===")
    print(f"id={response.id}")
    print(f"model={response.model}")
    for choice in response.choices:
        print(f"choice[{choice.index}].finish_reason={choice.finish_reason}")
        print(f"choice[{choice.index}].content={choice.message.content}")
    if response.usage:
        print(
            "usage: "
            f"prompt={response.usage.prompt_tokens}, "
            f"completion={response.usage.completion_tokens}, "
            f"total={response.usage.total_tokens}"
        )


def main() -> None:
    # 关闭 SDK 内置重试，确保示例中的退避过程清晰可见。
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )
    response = create_completion_with_retry(client)
    parse_response(response)


if __name__ == "__main__":
    main()
