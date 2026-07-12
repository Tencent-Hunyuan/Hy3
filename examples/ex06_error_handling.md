# 06 Error Handling & Retry：超时 / 限流 / 网络错误的重试与退避

生产环境中需要优雅地处理 API 异常。本示例使用指数退避策略对超时、限流（429）和网络错误进行重试。

## 完整请求

```python
import os
import time
import random
from openai import OpenAI, APIError, RateLimitError, APITimeoutError

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
    timeout=10,
)


def chat_with_retry(
    client: OpenAI,
    messages,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
):
    """
    带指数退避的重试封装。
    对 RateLimitError、APITimeoutError、APIError（含网络抖动）进行重试。
    """
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                temperature=0.7,
                max_tokens=256,
            )
            return response
        except RateLimitError as e:
            print(f"[Attempt {attempt + 1}] Rate limit: {e}")
        except APITimeoutError as e:
            print(f"[Attempt {attempt + 1}] Timeout: {e}")
        except APIError as e:
            status = getattr(e, "status", None)
            if status is not None and 400 <= status < 500:
                print(f"[Attempt {attempt + 1}] Client error ({status}), no retry: {e}")
                raise
            print(f"[Attempt {attempt + 1}] API error: {e}")
        except Exception as e:
            print(f"[Attempt {attempt + 1}] Unexpected error: {e}")
            raise

        if attempt < max_retries:
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, 0.5)
            sleep_time = delay + jitter
            print(f"  -> 等待 {sleep_time:.2f}s 后重试...")
            time.sleep(sleep_time)
        else:
            print("  -> 已达到最大重试次数，放弃请求。")
            raise


messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "用一句话总结重试机制的重要性。"},
]

try:
    response = chat_with_retry(client, messages)
    print("\n最终回答:", response.choices[0].message.content)
except Exception as e:
    print(f"\n请求最终失败: {e}")
```

## Response 解析

重试策略覆盖以下常见异常：

- `RateLimitError`（HTTP 429）：请求频率或并发超过配额，需要退避后重试。
- `APITimeoutError`：请求在客户端设置的超时时间内未返回，可重试。
- `APIError`：服务端返回的其他错误（如 5xx），通常也可重试。
- 其他异常：直接抛出，不再重试。

退避公式：

```text
delay = min(base_delay * (2 ^ attempt), max_delay) + jitter
```

加入随机抖动（jitter）可避免多个客户端在同一时刻同时重试，造成“惊群效应”。

## 示例输出

```text
[Attempt 1] Rate limit: Error code: 429 - {'error': {'message': 'Rate limit exceeded', 'type': 'rate_limit_error'}}
  -> 等待 1.23s 后重试...
[Attempt 2] Rate limit: Error code: 429 - {'error': {'message': 'Rate limit exceeded', 'type': 'rate_limit_error'}}
  -> 等待 2.67s 后重试...
[Attempt 3] Timeout: Request timed out.
  -> 等待 4.15s 后重试...

最终回答: 重试机制通过指数退避与抖动，在临时故障时提高请求成功率，同时避免对服务端造成二次冲击。
```

## 要点提示

1. 不要对所有异常都无限重试，设置合理的 `max_retries` 和 `max_delay`。
2. 幂等性：聊天补全接口天然幂等（相同输入得到相似输出），可安全重试。
3. 对于 4xx 客户端错误（如 401、404），通常不需要重试，应直接修复配置。
4. 生产环境可结合日志、监控与断路器模式进一步保障稳定性。
