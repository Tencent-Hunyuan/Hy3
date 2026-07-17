# 06 Error Handling & Retry：错误处理与退避

源码：[`06_error_handling_retry.py`](06_error_handling_retry.py)

## 运行

```bash
python 06_error_handling_retry.py
```

脚本不会主动制造限流。异常分支由 `tests/` 中的离线模拟测试覆盖，避免通过高频请求冲击真实服务。

## 完整请求

客户端关闭 SDK 内置重试，避免和示例重试策略叠加：

```python
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
    timeout=30.0,
    max_retries=0,
)

response = request_with_retry(
    client,
    {
        "model": "hy3",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 256,
        "extra_body": {"thinking": {"type": "disabled"}},
    },
)
```

## 重试决策

会有限重试：

- `APITimeoutError`；
- `APIConnectionError`；
- HTTP 408、409、429；
- HTTP 500、502、503、504。

不会自动重试参数、鉴权、权限、模型名和内容安全错误，例如 400、401、403、404、451。

429 响应可能包含 `Retry-After` 秒数或 HTTP 日期。脚本优先采用该值；缺失时使用：

```text
min(max_delay, base_delay * 2 ** (attempt - 1)) + 0%~25% jitter
```

默认最多尝试 4 次、单次等待预算 30 秒。如果服务端要求等待超过预算，示例停止并把决定权交给调用者，不会缩短服务端要求的等待时间。

## 完整响应与异常解析

成功时解析正文、`finish_reason` 和 `usage`。重试日志解析并输出：

- 异常类型；
- HTTP 状态；
- `request_id`；
- 当前尝试次数；
- 下一次等待时间。

日志不得包含 API Key 和敏感请求正文。

## 示例输出

限流后成功的模拟输出：

```text
attempt 1/4 failed: FakeStatusError, status=429, request_id=req-redacted; retrying in 2.00s
assistant: 随机抖动可以避免多个客户端在同一时刻再次请求，从而缓解惊群效应。
finish_reason: stop
usage: {'prompt_tokens': 24, 'completion_tokens': 39, 'total_tokens': 63}
```

注意：请求超时不代表服务端一定没有处理请求，重试可能产生重复生成和费用。具有外部副作用的工具调用还必须实现幂等键或去重。
