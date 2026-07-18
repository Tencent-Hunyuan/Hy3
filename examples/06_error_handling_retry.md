# 06 · Error Handling & Retry

## 说明

对可重试错误使用指数退避：

- 超时：`APITimeoutError`
- 限流：`RateLimitError` / HTTP 429
- 网络：`APIConnectionError`

退避：`delay ≈ base * 2^attempt`，超过最大次数后失败。

## 运行

```bash
python 06_error_handling_retry.py
```

## 实现要点

```python
client = OpenAI(..., timeout=30.0)

def with_retry(fn, max_retries=4, base_delay=0.8):
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except (RateLimitError, APITimeoutError, APIConnectionError):
            time.sleep(base_delay * (2 ** attempt))
    raise RuntimeError(...)
```

脚本包含：

1. 真实请求外包一层重试
2. 退避策略说明
3. 本地模拟超时以验证重试逻辑

## 示例输出

```text
=== normal call with retry wrapper ===
ok: OK

=== backoff policy (demo, no real failure required) ===
On RateLimitError / APITimeoutError / APIConnectionError:
  attempt 1 -> sleep ~0.8s then retry
  attempt 2 -> sleep ~1.6s then retry
  attempt 3 -> sleep ~3.2s then retry
  attempt 4 -> sleep ~6.4s then retry
After max_retries exhausted -> raise RuntimeError

=== flaky function + retry (local simulation) ===
[retry] simulated timeout #1; sleep 0.15s
[retry] simulated timeout #2; sleep 0.30s
result: success-after-retries
```
