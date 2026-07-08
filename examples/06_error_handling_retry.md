<p align="left">
    <a href="./zh-cn/06_error_handling_retry.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Example 06: Error handling & retry

This example demonstrates explicit retry with exponential backoff and jitter for timeout, rate limit, network errors, and retryable server errors.

> Related: [Examples Index](./README.md) | [API Quickstart](../quickstart.md)

## Run

```bash
python examples/06_error_handling_retry.py
```

## Full request

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请用三点说明 API 请求重试为什么需要退避和抖动。"}],
    temperature=0.3,
    max_tokens=512,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

## Response parsing

```python
print(response.choices[0].message.content)
print(response.usage)
```

## Retry policy

Retry:

- `RateLimitError` / HTTP `429`
- `APITimeoutError`
- `APIConnectionError`
- HTTP `500`, `502`, `503`, `504`

Do not blindly retry:

- HTTP `400`: request format, parameter, or chat-template issue
- HTTP `401` / `403`: authentication issue
- HTTP `404`: wrong endpoint or model name
- repeated tool execution errors that may cause side effects

## Sample output

```text
attempt 1: rate limited
retrying in 0.91s...
attempt 2: network/timeout error: APITimeoutError
retrying in 1.73s...
1. 退避可以避免大量请求在服务繁忙时继续冲击服务端。
2. 抖动可以防止多个客户端同时重试造成“惊群”。
3. 对可恢复错误重试、对参数错误快速失败，可以提升稳定性并减少无效请求。
usage: CompletionUsage(...)
```
