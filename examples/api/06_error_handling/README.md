# 06 Error Handling & Retry — 超时 / 限流 / 网络错误

演示如何识别可重试错误，遵守 `Retry-After`，并用指数退避做有限重试。

## 运行

```bash
cd examples/api
python 06_error_handling/main.py

# 离线演示分类与 mock 429：
HY3_MOCK=1 python 06_error_handling/main.py
```

## 策略

| 错误 | 是否重试 | 说明 |
|---|---|---|
| `429` 限流 | ✅ | 优先读 `Retry-After`（秒） |
| `408` / `502` / `503` / `504` | ✅ | 上游临时问题 |
| 连接失败 / 读超时 | ✅ | 网络抖动 |
| `400` 参数错误 | ❌ | 改请求后再发 |
| `401` / `403` | ❌ | 检查 Key / 权限 |
| `402` 额度 | ❌ | 调整套餐或配额 |

实现要点（见 `../common.py` 中 `with_retry`）：

1. `max_attempts` 限制次数  
2. `max_total_wait` 限制总等待预算  
3. 有 `Retry-After` 则按其等待；否则 `base * 2^(attempt-1) + jitter`

## 完整请求（被包装的业务调用）

```python
resp = with_retry(
    lambda: client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": "只回复：pong"}],
        max_tokens=16,
        temperature=0,
    ),
    max_attempts=4,
    max_total_wait=20.0,
    label="ping",
)
print(resp.choices[0].message.content)
```

等价 curl（失败时自行根据状态码决定是否重试）：

```bash
curl -sS -D - "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "只回复：pong"}],
    "max_tokens": 16
  }'
```

## 响应解析

成功：

```json
{
  "choices": [
    {
      "message": {"role": "assistant", "content": "pong"},
      "finish_reason": "stop"
    }
  ]
}
```

限流示意：

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 2

{"error": {"message": "rate limit exceeded", "type": "rate_limit_error"}}
```

## 示例输出（2026-07-18 TokenHub 实测）

```text
=== Retry classification ===
  RateLimitError   retryable=True
  Timeout          retryable=True
  Connection       retryable=True
  Auth 401         retryable=False
  Bad request 400  retryable=False
  Upstream 503     retryable=True

=== Backoff with Retry-After ===
  Retry-After honored → sleep 1.5s
=== Backoff without Retry-After (exp + jitter) ===
  attempt=1 suggested_wait≈1.05s
  attempt=2 suggested_wait≈2.37s
  attempt=3 suggested_wait≈4.31s

=== Wrapped live call (with_retry) ===
  success content='pong'
```

分类与退避为本地演示；最后的 `pong` 为真实 TokenHub 调用结果。离线可用 `HY3_MOCK=1` 观察模拟 429 重试。

生产环境请把重试逻辑下沉到统一 HTTP 客户端，并打点监控 429 / 5xx 比例。更多错误码见 [TokenHub API 错误码](https://cloud.tencent.com/document/product/1823/131595)。
