# 06 错误处理与重试 / Error Handling & Retry

[中文](#中文) | [English](#english)

---

## 中文

本示例展示如何处理 Hy3 API 调用中常见的错误场景，包括**超时**、**限流**、**网络错误**，并提供**指数退避重试**的实现。

---

### 常见错误类型

| 异常类 | HTTP 状态码 | 含义 | 建议处理 |
|:---|:---|:---|:---|
| `openai.APIConnectionError` | — | 网络连接失败 | 检查服务是否运行、网络是否通畅 |
| `openai.APITimeoutError` | — | 请求超时 | 增加 `timeout` 参数或减小 `max_tokens` |
| `openai.RateLimitError` | 429 | 请求频率超限 | 退避重试 |
| `openai.APIStatusError` | 5xx | 服务端内部错误 | 退避重试 |
| `openai.BadRequestError` | 400 | 请求参数错误 | 检查请求格式，无需重试 |
| `openai.NotFoundError` | 404 | 模型不存在 | 检查模型名称，无需重试 |

---

### 基础错误处理

```python
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError, APIStatusError

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

try:
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "你好"}],
        timeout=30.0,  # 30秒超时
    )
    print(response.choices[0].message.content)

except APIConnectionError as e:
    print(f"连接失败：{e}")
    print("请检查服务是否已启动，端口是否正确。")

except APITimeoutError as e:
    print(f"请求超时：{e}")
    print("请增加超时时间或减少 max_tokens。")

except RateLimitError as e:
    print(f"限流：{e}")
    print("请稍后重试。")

except APIStatusError as e:
    print(f"服务端错误 [{e.status_code}]：{e.message}")

except Exception as e:
    print(f"未知错误：{e}")
```

---

### 指数退避重试

对于临时性错误（限流、超时、服务端错误），使用指数退避策略自动重试：

```python
import time
from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIStatusError,
)

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

def call_with_retry(
    messages,
    max_retries=3,
    base_delay=1.0,
    timeout=60.0,
):
    """带指数退避的 API 调用"""
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                temperature=0.9,
                top_p=1.0,
                timeout=timeout,
            )
            return response

        except (APIConnectionError, APITimeoutError) as e:
            # 网络/超时错误：可重试
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  [尝试 {attempt+1}/{max_retries+1}] {type(e).__name__}，{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                print(f"  [尝试 {attempt+1}/{max_retries+1}] 重试次数用尽：{e}")
                raise

        except RateLimitError as e:
            # 限流错误：退避重试
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  [尝试 {attempt+1}/{max_retries+1}] 限流，{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                raise

        except APIStatusError as e:
            # 服务端 5xx 错误：可重试
            if e.status_code >= 500 and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"  [尝试 {attempt+1}/{max_retries+1}] 服务端错误 {e.status_code}，{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                raise

    return None  # 不应到达此处

# 使用
response = call_with_retry(
    messages=[{"role": "user", "content": "你好"}],
)
print(response.choices[0].message.content)
```

---

### 流式请求的错误处理

流式请求的错误可能在迭代过程中发生：

```python
def stream_with_retry(messages, max_retries=3, base_delay=1.0):
    """带重试的流式请求"""
    for attempt in range(max_retries + 1):
        try:
            stream = client.chat.completions.create(
                model="hy3",
                messages=messages,
                stream=True,
                timeout=60.0,
            )
            full_content = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    full_content += content
            return full_content

        except (APIConnectionError, APITimeoutError, RateLimitError) as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"\n  [重试 {attempt+1}] {type(e).__name__}，{delay:.1f}s 后重试...")
                time.sleep(delay)
            else:
                raise
```

---

## English

This example demonstrates how to handle common errors in Hy3 API calls, including **timeouts**, **rate limiting**, and **network errors**, with an **exponential backoff retry** implementation.

---

### Common Error Types

| Exception | HTTP Code | Meaning | Recommended Action |
|:---|:---|:---|:---|
| `APIConnectionError` | — | Network connection failed | Check server is running, port is correct |
| `APITimeoutError` | — | Request timed out | Increase `timeout` or reduce `max_tokens` |
| `RateLimitError` | 429 | Too many requests | Retry with backoff |
| `APIStatusError` | 5xx | Server error | Retry with backoff |
| `BadRequestError` | 400 | Invalid request | Fix request format, no retry |
| `NotFoundError` | 404 | Model not found | Check model name, no retry |

---

### Exponential Backoff Retry

```python
import time
from openai import OpenAI, APIConnectionError, APITimeoutError, RateLimitError, APIStatusError

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

def call_with_retry(messages, max_retries=3, base_delay=1.0, timeout=60.0):
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model="hy3", messages=messages, timeout=timeout,
            )
        except (APIConnectionError, APITimeoutError, RateLimitError) as e:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"[Attempt {attempt+1}] {type(e).__name__}, retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                raise
        except APIStatusError as e:
            if e.status_code >= 500 and attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                print(f"[Attempt {attempt+1}] Server error {e.status_code}, retrying in {delay:.1f}s...")
                time.sleep(delay)
            else:
                raise

response = call_with_retry(messages=[{"role": "user", "content": "Hello"}])
print(response.choices[0].message.content)
```

> **Tip**: Use retry for transient errors (429, 5xx, timeouts). Do NOT retry client errors (400, 404) — fix the request instead.
