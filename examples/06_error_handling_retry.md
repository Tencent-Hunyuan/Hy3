# 示例 06：错误处理与重试（超时 / 限流 / 网络错误）

> 对应脚本：[`06_error_handling_retry.py`](06_error_handling_retry.py)

线上调用不可避免会遇到限流、网关错误、网络抖动。本示例给出一个“生产级”重试器：区分可重试 / 不可重试错误，优先遵守 `Retry-After`，退避带 jitter，并设总等待预算。

## 错误分类

| 状态码 / 类型 | 可重试？ | 处理 |
|---|---|---|
| 429 | ✅ | 遵守 `Retry-After` + 指数退避 |
| 502 / 503 / 504 | ✅ | 上游临时故障，退避重试 |
| 连接失败 / 超时 | ✅ | 检查网络 / 代理后重试 |
| 400 / 401 / 403 | ❌ | 立即修正（格式 / Key / 权限），不可重试 |

## 完整请求

请求本身和示例 01 一样，区别是包在 `call_with_retry` 里：

```python
response = call_with_retry(
    lambda: client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "说「你好」两个字。"}],
        max_tokens=32,
        extra_body=REASONING,
    )
)
```

## 重试器核心逻辑

```python
def call_with_retry(fn):
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return fn()
        except Exception as err:
            if not is_retryable(err) or attempt >= MAX_ATTEMPTS:
                raise
            ra = parse_retry_after(err)          # 优先用 Retry-After 头
            delay = ra if ra is not None else backoff(attempt)   # 否则指数退避 + jitter
            time.sleep(delay)
```

参数：`MAX_ATTEMPTS=4`、`BASE_DELAY=0.5`、`MAX_DELAY=8`、`MAX_TOTAL_WAIT=20`。

## 完整响应解析

成功时响应结构与示例 01 完全相同，按 `choices[0].message.content` 取回答即可。失败时抛出的异常类型来自 `openai` 包：`APIError` / `APITimeoutError` / `APIConnectionError`，可用 `status_code` 和 `response.headers` 判断。

## 示例输出

正常（无重试）：
```
=== 带重试的请求 ===
回答：你好。
```

错误密钥（401 Unauthorized，不可重试）：
```
=== 带重试的请求 ===
请求失败: AuthenticationError (HTTP 401)
```

错误模型名称（400 Bad Request，不可重试）：
```
=== 带重试的请求 ===
请求失败: BadRequestError (HTTP 400)
```

无法连接（服务未启动 / 网络不通，可重试）：
```
=== 带重试的请求 ===
  第 1 次重试, 等待 0.5s (HTTP APIConnectionError)
  第 2 次重试, 等待 0.5s (HTTP APIConnectionError)
  第 3 次重试, 等待 1.5s (HTTP APIConnectionError)
请求失败: APIConnectionError
```
