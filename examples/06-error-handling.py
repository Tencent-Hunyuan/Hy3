#!/usr/bin/env python3
"""
Hy3 API Example 06 — Error Handling & Retry（超时/限流/网络错误的重试与退避）

用法：
    python 06-error-handling.py

前置条件：
    pip install openai
    Hy3 已通过 vLLM/SGLang 部署在 http://127.0.0.1:8000/v1
"""

import time
import random
from openai import (
    OpenAI,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
)

BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = [redacted]
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=[redacted], timeout=30.0)


# ─── 1. 指数退避重试 ──────────────────────
def call_with_retry(messages, max_retries=3, base_delay=1.0):
    """
    带指数退避的重试机制

    退避策略：
      第 1 次重试：等 base_delay * 2^0 = 1s
      第 2 次重试：等 base_delay * 2^1 = 2s
      第 3 次重试：等 base_delay * 2^2 = 4s
    加上随机抖动（jitter）避免惊群效应
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.9,
                top_p=1.0,
            )
        except RateLimitError as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"  ⚠️ 限流，{delay:.1f}s 后重试 (第 {attempt+1}/{max_retries} 次)...")
                time.sleep(delay)
        except APITimeoutError as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  ⚠️ 超时，{delay:.1f}s 后重试 (第 {attempt+1}/{max_retries} 次)...")
                time.sleep(delay)
        except APIConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  ⚠️ 连接错误，{delay:.1f}s 后重试 (第 {attempt+1}/{max_retries} 次)...")
                time.sleep(delay)
        except APIStatusError as e:
            # 5xx 服务端错误重试，4xx 客户端错误不重试
            if 500 <= e.status_code < 600 and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  ⚠️ 服务端错误 {e.status_code}，{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                raise  # 4xx 错误直接抛出

    raise last_exception


# ─── 2. 超时控制 ──────────────────────────
def call_with_timeout(messages, connect_timeout=5.0, read_timeout=30.0):
    """设置连接超时和读取超时"""
    try:
        return client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.9,
            top_p=1.0,
            timeout=read_timeout,  # httpx 的 read timeout
        )
    except APITimeoutError:
        print("  ❌ 请求超时！请检查网络连接或增加 timeout 参数。")
        return None


# ─── 3. 演示 ──────────────────────────────
def demo_retry():
    """演示重试机制"""
    print("=" * 60)
    print("  📝 Example 6.1 — 指数退避重试")
    print("=" * 60)

    try:
        response = call_with_retry(
            [{"role": "user", "content": "Hello!"}],
            max_retries=3,
        )
        print(f"  ✅ 成功: {response.choices[0].message.content}")
    except Exception as e:
        print(f"  ❌ 最终失败: {type(e).__name__}: {e}")


def demo_timeout():
    """演示超时控制"""
    print("\n" + "=" * 60)
    print("  📝 Example 6.2 — 超时控制")
    print("=" * 60)

    response = call_with_timeout(
        [{"role": "user", "content": "说一个笑话"}],
        read_timeout=30.0,
    )
    if response:
        print(f"  ✅ 成功: {response.choices[0].message.content[:50]}...")


def demo_error_handling_flow():
    """展示完整的错误处理流程"""
    print("\n" + "=" * 60)
    print("  📊 推荐错误处理流程")
    print("=" * 60)
    print("""
  请求 API
      │
      ├── 200 OK ──────────────→ 解析 response ✅
      │
      ├── 4xx (400/401/403) ──→ 检查参数/API Key，不重试 ❌
      │
      ├── 429 (Rate Limit) ───→ 等 Retry-After 秒后重试 ⚠️
      │
      ├── 5xx (500/502/503) ──→ 指数退避重试（最多3次） ⚠️
      │
      ├── Timeout ─────────────→ 检查 timeout 参数，重试 ⚠️
      │
      └── Connection Error ────→ 检查 Base URL、防火墙 ⚠️

  最佳实践：
  1. 始终设置 timeout（连接 + 读取）
  2. 4xx 错误不重试（客户端问题）
  3. 5xx + 429 用指数退避重试
  4. 加 jitter（随机抖动）避免惊群
  5. 设最大重试次数，防止无限循环
  6. 记录每次重试的日志，方便排查
  """)


if __name__ == "__main__":
    demo_retry()
    demo_timeout()
    demo_error_handling_flow()
