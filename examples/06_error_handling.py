"""
Example 6: Error Handling & Retry — timeout, rate limit, connection errors, exponential backoff

Prerequisites:
  - pip install openai tenacity
"""

import time
import random
from openai import OpenAI, (
    APITimeoutError,
    RateLimitError,
    APIConnectionError,
    InternalServerError,
)

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

# 1. 超时处理
print("=" * 60)
print("1. 超时处理（Timeout）")
print("=" * 60)

try:
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "讲一个很长的故事。"}],
        max_tokens=2048,
        timeout=0.001,
    )
    print("成功:", response.choices[0].message.content[:50])
except APITimeoutError as e:
    print(f"捕获超时错误: {e}")
    print("→ 建议: 增加 timeout 参数或检查网络连接")

# 2. 限流处理
print("\n" + "=" * 60)
print("2. 限流处理（模拟 Rate Limit）")
print("=" * 60)

try:
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "你好"}],
        max_tokens=10,
    )
    print(f"正常响应: {response.choices[0].message.content}")
except RateLimitError as e:
    print(f"捕获限流错误: {e}")
    print("→ 建议: 等待后重试，降低请求频率")
    retry_after = getattr(e, 'response', {}).get('headers', {}).get('retry-after', 5)
    print(f"  Retry-After: {retry_after}s")

# 3. 网络错误处理
print("\n" + "=" * 60)
print("3. 网络错误处理")
print("=" * 60)

try:
    bad_client = OpenAI(base_url="http://127.0.0.1:19999/v1", api_key="EMPTY", timeout=3)
    response = bad_client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "你好"}],
    )
except APIConnectionError as e:
    print(f"捕获网络连接错误: {e}")
    print("→ 建议: 检查服务是否正在运行，base_url 是否正确")

# 4. 指数退避重试
print("\n" + "=" * 60)
print("4. 指数退避重试")
print("=" * 60)


def call_with_retry(messages, max_retries=5, base_delay=1.0, **kwargs):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                jitter = random.uniform(0, 0.5)
                total_delay = delay + jitter
                print(f"  第 {attempt} 次重试，等待 {total_delay:.1f}s...")
                time.sleep(total_delay)

            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                timeout=30,
                **kwargs,
            )
            return response

        except (APITimeoutError, RateLimitError, APIConnectionError,
                InternalServerError) as e:
            last_error = e
            print(f"  请求失败 (尝试 {attempt}/{max_retries}): {type(e).__name__}")
            if attempt == max_retries:
                print(f"  达到最大重试次数，放弃")
                raise last_error
            continue

    raise last_error


print("发起请求（带指数退避重试）...")
try:
    resp = call_with_retry(
        messages=[{"role": "user", "content": "用一句话解释 TCP 和 UDP 的区别。"}],
        max_retries=3,
        base_delay=0.5,
        temperature=0.7,
    )
    print(f"\n成功! 回答: {resp.choices[0].message.content}")
except Exception as e:
    print(f"\n最终失败: {e}")

print("\n" + "=" * 60)
print("错误处理策略总结")
print("=" * 60)
summary = """
┌──────────────┬───────────────────────┬──────────────────────────────┐
│  错误类型     │  捕获异常              │  处理策略                     │
├──────────────┼───────────────────────┼──────────────────────────────┤
│  超时         │  APITimeoutError      │  增加 timeout / 减小 max_tokens │
│  限流 429     │  RateLimitError       │  指数退避 + 降低并发           │
│  网络错误     │  APIConnectionError   │  检查服务状态 / base_url       │
│  服务端错误   │  InternalServerError  │  退避重试 / 联系运维            │
│  通用错误     │  APIError             │  记录日志 / 告警               │
└──────────────┴───────────────────────┴──────────────────────────────┘
"""
print(summary)
