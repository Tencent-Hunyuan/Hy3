# Error handling & retry：错误处理与退避

运行：

```bash
python api/examples/06_error_handling_retry/error_handling_retry.py
```
完整请求与异常处理见 [`error_handling_retry.py`](error_handling_retry.py)。示例将 SDK 的 `max_retries` 设为 `0`，避免 SDK 重试与应用重试叠加；客户端设置 20 秒超时，然后对连接错误、超时、`429` 和 `5xx` 最多尝试 5 次。

```python
client = create_client(max_retries=0, timeout=20.0)
response = call_with_retry(lambda: client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "用一句话解释指数退避。"}],
    max_tokens=128,
))
```

服务器有 `Retry-After` 时优先采用（最大 30 秒），否则使用 `1, 2, 4, 8...` 秒的指数退避并加入随机抖动。最后一次失败会原样抛出，便于上层记录和告警。`400`、`401`、`403`、`404` 不重试，因为它们通常需要修正请求或配置。

```text
attempt 1/5 failed: RateLimitError; retry in 2.00s
attempt 2/5 failed: APITimeoutError; retry in 2.17s
id: chatcmpl-f61
model: hy3
role: assistant
content: 指数退避是在连续失败后按指数增长等待时间再重试的策略。
finish_reason: stop
usage: prompt=16, completion=25, total=41
```
