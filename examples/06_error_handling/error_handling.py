"""
Hy3 API 示例 6：错误处理与重试
===============================

演示如何处理 Hy3 API 调用中的常见错误：
  1. 超时重试（timeout）
  2. 限流重试（HTTP 429 Rate Limit）
  3. 网络错误重试（ConnectionError）
  4. 通用指数退避重试装饰器

前置条件：
  - 在 https://console.cloud.tencent.com/tokenhub/apikey 创建 API Key
  - 安装 openai: pip install openai

运行方式：
  python error_handling.py
"""

import time
import random
from typing import Callable, Any

from openai import OpenAI, APITimeoutError, RateLimitError, APIConnectionError

API_KEY = "sk-你的APIKey"  # TODO: 替换为真实的 API Key

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=API_KEY,
    timeout=30.0,
    max_retries=0,  # 我们手动控制重试，便于演示
)


# ============================================================
# 1. 指数退避 + jitter 工具函数
# ============================================================
def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
    """计算指数退避延迟（带随机 jitter）"""
    delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, delay * 0.1)  # 10% jitter
    return delay + jitter


# ============================================================
# 2. 通用重试装饰器
# ============================================================
def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (APITimeoutError, RateLimitError, APIConnectionError),
):
    """通用指数退避重试装饰器"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = exponential_backoff(attempt, base_delay, max_delay)
                        print(f"  ⚠️ 第 {attempt + 1} 次失败: {type(e).__name__}")
                        print(f"  ⏳ 等待 {delay:.1f}s 后重试 ({max_retries - attempt} 次剩余)...")
                        time.sleep(delay)
                    else:
                        print(f"  ❌ 已达最大重试次数 ({max_retries})，放弃")
                        raise
                except Exception:
                    # 非可重试异常，直接抛出
                    raise
            raise last_exception
        return wrapper
    return decorator


# ============================================================
# 3. 示例 1: 超时处理
# ============================================================
def demo_timeout():
    print("=" * 60)
    print("【示例 1: 超时重试】")
    print("=" * 60)

    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def call_with_timeout():
        return client.chat.completions.create(
            model="hy3",
            messages=[{"role": "user", "content": "请用一句话回答：1+1=?"}],
            timeout=0.001,  # 1ms 超时，几乎必定触发
            extra_body={"reasoning_effort": "no_think"},
        )

    try:
        response = call_with_timeout()
        print(f"  回答: {response.choices[0].message.content}")
    except APITimeoutError:
        print("  ❌ 最终: 请求超时，建议增加 timeout 值")

    # 正确做法：使用合理超时
    print("\n  ✅ 正确做法：使用合理超时")
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "1+1=?"}],
        timeout=60.0,  # 给足超时时间
        extra_body={"reasoning_effort": "no_think"},
    )
    print(f"  回答: {response.choices[0].message.content}")


# ============================================================
# 4. 示例 2: 限流处理
# ============================================================
def demo_rate_limit():
    print("\n" + "=" * 60)
    print("【示例 2: 限流重试】")
    print("=" * 60)

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def call_safe():
        return client.chat.completions.create(
            model="hy3",
            messages=[{"role": "user", "content": "今天天气怎么样？"}],
            extra_body={"reasoning_effort": "no_think"},
        )

    print("  提示: 生产环境建议:")
    print("  - 启用 client 的 max_retries 参数")
    print("  - 或使用上面的 retry_with_backoff 装饰器")
    print("  - 捕获 RateLimitError 后使用指数退避")

    try:
        response = call_safe()
        print(f"  ✅ 成功获取响应: {response.choices[0].message.content[:50]}...")
    except RateLimitError as e:
        print(f"  ❌ 限流: {e}")


# ============================================================
# 5. 示例 3: 网络错误处理
# ============================================================
def demo_network_error():
    print("\n" + "=" * 60)
    print("【示例 3: 网络错误处理】")
    print("=" * 60)

    # 使用错误的 URL 模拟连接失败
    bad_client = OpenAI(
        base_url="https://invalid-endpoint.example.com/v1",
        api_key=API_KEY,
        timeout=3.0,
    )

    @retry_with_backoff(max_retries=2, base_delay=1.0)
    def call_with_bad_url():
        return bad_client.chat.completions.create(
            model="hy3",
            messages=[{"role": "user", "content": "你好"}],
            extra_body={"reasoning_effort": "no_think"},
        )

    try:
        call_with_bad_url()
    except APIConnectionError as e:
        print(f"  ❌ 最终: 连接失败: {type(e).__name__}")
        print(f"  ✅ 解决方法: 检查 URL、网络连接、API Key 是否正确")


# ============================================================
# 6. 示例 4: 健壮的调用函数（可直接用于生产）
# ============================================================
@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0)
def robust_chat_completion(client: OpenAI, messages: list, **kwargs):
    """健壮的聊天补全调用 —— 带自动重试和指数退避"""
    return client.chat.completions.create(
        model=kwargs.get("model", "hy3"),
        messages=messages,
        temperature=kwargs.get("temperature", 0.7),
        top_p=kwargs.get("top_p", 1.0),
        timeout=kwargs.get("timeout", 60.0),
        extra_body={"reasoning_effort": kwargs.get("reasoning_effort", "no_think")},
    )


def demo_robust_call():
    print("\n" + "=" * 60)
    print("【示例 4: 生产级健壮调用】")
    print("=" * 60)

    try:
        response = robust_chat_completion(
            client,
            [{"role": "user", "content": "用一句话说明什么是 API 错误重试。"}],
            temperature=0.7,
            timeout=60.0,
            reasoning_effort="no_think",
        )
        print(f"  ✅ 回答: {response.choices[0].message.content}")
        print(f"  📊 用量: prompt={response.usage.prompt_tokens}, "
              f"completion={response.usage.completion_tokens}, "
              f"total={response.usage.total_tokens}")
    except Exception as e:
        print(f"  ❌ 最终失败: {type(e).__name__}: {e}")


# ============================================================
# 运行所有示例
# ============================================================
if __name__ == "__main__":
    print("Hy3 API 错误处理与重试示例\n")
    print(f"API Endpoint: {client.base_url}\n")

    demo_timeout()
    demo_rate_limit()
    demo_network_error()
    demo_robust_call()

    print("\n" + "=" * 60)
    print("总结:")
    print("  - 超时错误 → 增加 timeout 值 + 重试")
    print("  - 限流错误 → 指数退避 + jitter + 重试")
    print("  - 连接错误 → 检查网络 + 重试")
    print("  - 通用方案 → retry_with_backoff 装饰器")
    print("=" * 60)
