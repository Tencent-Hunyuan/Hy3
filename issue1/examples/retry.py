#!/usr/bin/env python3
"""
Hy3 API 错误处理与重试示例：超时、限流、网络异常的重试策略。

使用方式：
    cd issue1
    python examples/retry.py

前置条件：
    1. 复制 .env.example 为 .env 并填入 HY3_API_KEY
    2. pip install "openai>=1.0.0" python-dotenv

可选配置（环境变量）：
    HY3_TIMEOUT=30            # 请求超时秒数
    HY3_RETRY_MAX_ATTEMPTS=5  # 最大重试次数
"""

import os
import sys
import time
import random
from pathlib import Path
from typing import Callable, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import (
    OpenAI,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
API_KEY = os.getenv("HY3_API_KEY", "")
MODEL = os.getenv("HY3_MODEL", "hy3-preview")

TIMEOUT = float(os.getenv("HY3_TIMEOUT", "90"))
MAX_ATTEMPTS = int(os.getenv("HY3_RETRY_MAX_ATTEMPTS", "5"))

T = TypeVar("T")

# ── 错误分类 ─────────────────────────────────────────

# 不可重试的错误：重试也解决不了
NON_RETRYABLE = (
    BadRequestError,       # 请求格式错误
    AuthenticationError,   # 鉴权失败 (401)
    PermissionDeniedError, # 权限不足 (403)
    NotFoundError,         # 模型不存在 (404)
)

# 可重试的 HTTP 状态码
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def is_retryable(error: Exception) -> bool:
    """判断错误是否值得重试。"""
    # 不可重试类型
    if isinstance(error, NON_RETRYABLE):
        return False
    # 网络/超时/限流 → 重试
    if isinstance(error, (APIConnectionError, APITimeoutError, RateLimitError)):
        return True
    # HTTP 状态码判断
    if isinstance(error, APIStatusError):
        return error.status_code in RETRYABLE_STATUS
    return False


def backoff(attempt: int) -> float:
    """指数退避 + 随机抖动。"""
    base = min(8.0, 0.5 * (2 ** (attempt - 1)))  # 0.5s, 1s, 2s, 4s, 8s(max)
    jitter = random.uniform(0, 0.25)
    return base + jitter


# ── 重试核心逻辑 ─────────────────────────────────────

def call_with_retry(
    fn: Callable[[], T],
    max_attempts: int = MAX_ATTEMPTS,
) -> T:
    """带指数退避重试的 API 调用包装器。

    Args:
        fn: 需要执行的 API 调用（无参 lambda）
        max_attempts: 最大尝试次数（含首次）

    Returns:
        API 调用结果

    Raises:
        原始异常（如果所有重试都失败）
    """
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = fn()
            print(f"  ✅ attempt={attempt}/{max_attempts} → 成功")
            return result
        except Exception as exc:
            last_error = exc
            retryable = is_retryable(exc)

            if not retryable:
                print(f"  ❌ attempt={attempt}/{max_attempts} → 不可重试错误: {type(exc).__name__}: {exc}")
                raise

            if attempt == max_attempts:
                print(f"  ❌ attempt={attempt}/{max_attempts} → 已达最大重试次数: {type(exc).__name__}: {exc}")
                raise

            wait = backoff(attempt)
            status = getattr(exc, "status_code", "N/A")
            print(f"  ⚠️  attempt={attempt}/{max_attempts} → {type(exc).__name__} (status={status}), "
                  f"{wait:.2f}s 后重试...")
            time.sleep(wait)

    # 理论上不会到达这里
    raise last_error  # type: ignore[misc]


# ── 模拟各类错误场景 ─────────────────────────────────

def simulate_errors():
    """展示不同错误类型的分类结果（使用静态表，避免 mock SDK 内部对象）。"""
    print(f"\n{'─' * 50}")
    print("【错误分类参考表】")
    print(f"{'─' * 50}")
    print(f"{'错误类型':<30s} {'可重试':<10s} {'说明'}")
    print("-" * 60)

    rows = [
        ("BadRequestError",          "❌ 不可重试", "请求格式错误，修正后重试"),
        ("AuthenticationError",      "❌ 不可重试", "API Key 无效，检查配置"),
        ("PermissionDeniedError",    "❌ 不可重试", "权限不足，检查套餐"),
        ("NotFoundError",            "❌ 不可重试", "模型名错误"),
        ("APIConnectionError",       "✅ 可重试",   "网络断开，可重试"),
        ("APITimeoutError",          "✅ 可重试",   "请求超时，可重试"),
        ("RateLimitError",           "✅ 可重试",   "被限流，可重试"),
        ("APIStatusError(408/425)",  "✅ 可重试",   "服务端临时错误"),
        ("APIStatusError(429)",      "✅ 可重试",   "速率限制"),
        ("APIStatusError(5xx)",      "✅ 可重试",   "服务端内部错误"),
    ]

    for name, retryable, desc in rows:
        print(f"{name:<30s} {retryable:<10s} {desc}")


def main():
    print("=" * 60)
    print("【Hy3 API 错误处理与重试】")
    print(f"模型: {MODEL}")
    print(f"超时设置: {TIMEOUT}s")
    print(f"最大重试: {MAX_ATTEMPTS} 次")
    print("=" * 60)

    simulate_errors()

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=TIMEOUT)

    print(f"\n{'─' * 50}")
    print("【正常请求（带重试保护）】")
    print(f"{'─' * 50}")

    def make_request():
        return client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "请列出安全重试 Hy3 API 请求的 5 条最佳实践。",
                }
            ],
            temperature=0.3,
            top_p=1.0,
            max_tokens=256,
        )

    print(f"\n请求: {make_request.__doc__}")
    print()

    response = call_with_retry(make_request)

    choice = response.choices[0]
    print(f"\n{'─' * 50}")
    print("【响应内容】")
    print(f"{'─' * 50}")
    print(f"id: {response.id}")
    print(f"model: {response.model}")
    print(f"finish_reason: {choice.finish_reason}")
    print(f"content:\n{choice.message.content}")
    if response.usage:
        u = response.usage
        print(f"\nToken: prompt={u.prompt_tokens}, completion={u.completion_tokens}, total={u.total_tokens}")

    print(f"\n✅ retry 示例运行完成！")


if __name__ == "__main__":
    main()
