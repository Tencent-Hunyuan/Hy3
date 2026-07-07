# Error Handling and Retry

演示超时、限流、网络错误和临时 5xx 的重试与退避。脚本不会重试明显永久失败的请求，例如参数错误、鉴权失败、权限不足和模型不存在。

运行：

```bash
python3 examples/api/retry.py
```

可选配置：

```bash
export HY3_TIMEOUT="30"
export HY3_RETRY_MAX_ATTEMPTS="5"
```

## 完整请求

下面展示本地 vLLM/SGLang 默认请求。使用 OpenRouter、腾讯云或其他远程 provider 时，脚本会根据 `examples/api/common.py` 的配置去掉 Hy3 本地模板参数或合并 `HY3_EXTRA_BODY_JSON`；运行时打印的 request 是实际发送内容。

```python
{
    "model": "hy3",
    "messages": [
        {
            "role": "user",
            "content": "Give a compact checklist for retrying Hy3 API requests safely.",
        }
    ],
    "temperature": 0.3,
    "top_p": 1.0,
    "max_tokens": 256,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think",
        }
    },
}
```

## 完整 response 解析

成功后脚本解析：

```python
choice = response.choices[0]
message = choice.message

print("id:", response.id)
print("model:", response.model)
print("finish_reason:", choice.finish_reason)
print("content:", message.content)
print("usage:", response.usage)
```

## 重试策略

会重试：

- `APIConnectionError`
- `APITimeoutError`
- `RateLimitError`
- HTTP `408`, `409`, `425`, `429`, `500`, `502`, `503`, `504`

不会重试：

- `BadRequestError`
- `AuthenticationError`
- `PermissionDeniedError`
- `NotFoundError`

退避公式：

```python
base = min(8.0, 0.5 * (2 ** (attempt - 1)))
jitter = random.uniform(0.0, 0.25)
sleep_s = base + jitter
```

## 示例输出

以下输出来自实际调用 OpenRouter `tencent/hy3:free`：

```text
attempt=1 status=success

=== parsed response ===
id: gen-1783435763-8gXkk17QfMYqSBQIDnpb
model: tencent/hy3-20260706:free
finish_reason: stop
content: **Compact Checklist: Safe Retries for Hy3 API Requests**

- [ ] **Idempotency**: Use idempotency keys / safe methods (GET, conditional PUT) to avoid duplicate side effects.
- [ ] **Retry triggers**: Retry only on 429, 500–503, timeouts, or connection errors. Do **not** retry 4xx (except 429/408).
- [ ] **Backoff**: Use exponential backoff + jitter (e.g., base 0.5s, cap 10s).
- [ ] **Limit**: Max 3–5 attempts; fail fast after limit.
- [ ] **Respect headers**: Honor `Retry-After` on 429/503.
- [ ] **Timeouts**: Set per-request and total deadline; cancel hung calls.
- [ ] **Concurrency**: Cap parallel retries; avoid thundering herd.
- [ ] **Observability**: Log attempt count, status, latency; alert on spike.
- [ ] **Token/session**: Refresh auth before retry if 401 on first attempt only.
- [ ] **Circuit breaker**: Open circuit on sustained failures; half-open to test recovery.
```
