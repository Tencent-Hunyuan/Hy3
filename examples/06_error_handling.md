# Example 6: Error Handling & Retry — 超时/限流/网络错误的重试与退避

## 错误类型

| 错误类型 | 异常类 | 处理策略 |
|----------|--------|----------|
| 超时 | `APITimeoutError` | 增加 timeout / 减小 max_tokens |
| 限流 429 | `RateLimitError` | 指数退避 + 降低并发 |
| 网络错误 | `APIConnectionError` | 检查服务状态 / base_url |
| 服务端错误 | `InternalServerError` | 退避重试 / 联系运维 |

## 指数退避

```
delay = base_delay × 2^(attempt - 1) + random_jitter
```

| 重试次数 | 等待时间 |
|----------|----------|
| 1 | 1.0 ~ 1.5s |
| 2 | 2.0 ~ 2.5s |
| 3 | 4.0 ~ 4.5s |
| 4 | 8.0 ~ 8.5s |
| 5 | 16.0 ~ 16.5s |

## tenacity 写法

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type((
        APITimeoutError, RateLimitError, APIConnectionError
    )),
)
def call_hy3(client, messages, **kwargs):
    return client.chat.completions.create(
        model="hy3", messages=messages, timeout=30, **kwargs,
    )
```

## 示例输出

```
============================================================
1. 超时处理（Timeout）
============================================================
捕获超时错误: Request timed out: 0.001s
→ 建议: 增加 timeout 参数或检查网络连接

============================================================
2. 限流处理（模拟 Rate Limit）
============================================================
正常响应: 你好！有什么可以帮助你的吗？

============================================================
3. 网络错误处理
============================================================
捕获网络连接错误: Connection refused
→ 建议: 检查服务是否正在运行，base_url 是否正确

============================================================
4. 指数退避重试
============================================================
发起请求（带指数退避重试）...
  第 1 次重试，等待 0.5s...
  第 2 次重试，等待 1.0s...
成功! 回答: TCP 是面向连接的可靠传输协议，UDP 是无连接的不可靠传输协议。
```
