# 06 Error Handling & Retry

这个示例演示如何为 Hy3 API 调用增加基础错误处理和重试逻辑，重点处理三类适合
重试的临时性问题：

- `RateLimitError`：请求过于频繁或触发限流。
- `APITimeoutError`：请求超过客户端超时时间。
- `APIConnectionError`：网络连接、代理或服务地址异常。

脚本位置：[06_error_handling_retry.py](06_error_handling_retry.py)。

## 示例功能

示例使用 OpenAI Python SDK 创建 Hy3 客户端，并设置 30 秒超时：

```python
client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
    timeout=30.0,
)
```

请求失败时，脚本会使用指数退避加随机抖动：

```python
sleep_seconds = min(2 ** attempt, 16) + random.uniform(0, 0.5)
```

也就是说，前几次重试大约等待 1 秒、2 秒、4 秒、8 秒，最长退避时间限制在
16 秒附近。额外的随机抖动可以减少大量客户端同时重试造成的请求尖峰。

## 完整请求

核心请求在 `chat_with_retry()` 中发起：

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "Give one sentence about robust API clients.",
        }
    ],
    max_tokens=128,
)
```

关键参数：

| 参数 | 说明 |
| --- | --- |
| `model` | 要调用的 Hy3 模型名，可通过 `HY3_MODEL` 环境变量覆盖 |
| `messages` | OpenAI Chat Completions 格式的对话消息 |
| `max_tokens` | 限制本次回答最多生成的 token 数 |
| `timeout` | 在创建 `OpenAI(...)` 客户端时设置，控制单次请求最长等待时间 |

## 重试逻辑

完整重试函数如下：

```python
def chat_with_retry(max_retries=4):
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": "Give one sentence about robust API clients.",
                    }
                ],
                max_tokens=128,
            )
        except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
            if attempt == max_retries:
                raise

            sleep_seconds = min(2 ** attempt, 16) + random.uniform(0, 0.5)
            print(f"{type(exc).__name__}: retrying in {sleep_seconds:.1f}s...")
            time.sleep(sleep_seconds)
```

这里的处理策略是：

| 场景 | 是否重试 | 原因 |
| --- | --- | --- |
| `RateLimitError` | 是 | 限流通常可以等待后再次请求 |
| `APITimeoutError` | 是 | 服务端可能仍可在下一次请求中正常响应 |
| `APIConnectionError` | 是 | 网络抖动、代理异常或连接中断可能是临时问题 |
| 认证失败、参数错误、模型不存在 | 否 | 这类错误通常需要修改配置或请求参数，重试没有意义 |

如果所有重试都失败，函数会重新抛出最后一次异常，方便上层应用记录日志、告警或
返回明确的错误信息。

## 完整 response 解析

`chat.completions.create(...)` 成功后会返回完整的非流式响应。当前示例只读取第一
个候选回答：

```python
response = chat_with_retry()
print(response.choices[0].message.content)
```

可以把返回结构理解为：

```text
response
└── choices[0]
    └── message
        └── content = 模型最终回答文本
```

如果需要记录更多信息，可以同时读取 `response.id`、`response.model`、
`response.usage` 等字段，具体字段取决于服务端返回内容。

## 运行

先安装依赖并配置 API 信息：

```bash
pip install -r examples/requirements.txt
```

Windows PowerShell：

```powershell
$env:HY3_BASE_URL = "http://127.0.0.1:8000/v1"
$env:HY3_API_KEY = "EMPTY"
$env:HY3_MODEL = "hy3"
python examples/06_error_handling_retry.py
```

macOS / Linux：

```bash
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
python examples/06_error_handling_retry.py
```

## 示例输出

请求一次成功时，输出类似：

```text
Robust API clients set explicit timeouts, retry transient failures with backoff, and surface clear errors when recovery is not possible.
```

如果第一次请求遇到网络错误或限流，可能先看到重试日志：

```text
RateLimitError: retrying in 1.3s...
RateLimitError: retrying in 2.2s...
Robust API clients use timeouts, retries with exponential backoff, and clear error handling to stay reliable under transient failures.
```

## 实践建议

- 只重试临时性错误，不要盲目重试认证失败、参数错误或模型不存在等配置问题。
- 为每次请求设置明确的 `timeout`，避免应用无限等待。
- 使用指数退避和随机抖动，避免在限流后立即集中重试。
- 如果请求会触发外部副作用，例如写数据库、发消息、扣费或调用真实工具，需要额外
  设计幂等机制，避免重试导致重复执行。
- 生产环境建议记录每次失败的异常类型、重试次数、等待时间和最终状态。
