# 06 错误处理与重试

这个示例只重试临时错误，并限制尝试次数和总等待时间。SDK 自带重试已关闭，避免
SDK 和业务代码重复重试。完整代码见
[06_error_handling_retry.py](06_error_handling_retry.py)。

## 请求和重试策略

```python
policy = RetryPolicy(
    max_attempts=4,
    base_delay=0.5,
    max_delay=8.0,
    max_total_wait=20.0,
)

response = call_with_retry(
    lambda: client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": "用一句话解释指数退避。"}],
        temperature=0.2,
        max_tokens=256,
        extra_body={"thinking": {"type": "disabled"}},
    ),
    policy=policy,
    on_retry=report_retry,
)
```

| 错误 | 自动重试 | 处理 |
|---|---|---|
| 400/401/402/403 | 否 | 修正参数、Key、权限、地域、余额或额度。 |
| 429 | 是，有限 | 优先遵守 `Retry-After`；再检查 RPM/TPM/TPD/并发限制。 |
| 502/503/504 | 是，有限 | 指数退避 + equal jitter。 |
| SDK 连接错误/超时 | 是，有限 | 同上。 |
| 其他状态 | 否 | 原样向上抛出，不猜测可重试性。 |

`Retry-After` 支持秒数和 HTTP date；它不会被 jitter 改写。若下一次等待会超过
`max_total_wait`，抛出 `RetryBudgetExceeded`。达到 `max_attempts` 后抛出最后一个
原始错误，避免无限循环。

## 运行结果

```powershell
python examples/api/06_error_handling_retry.py
```

正常调用可能不会触发重试，离线测试使用模拟的 401/429/502/503/504、timeout 和
connection error 覆盖各分支。2026-07-17 在 TokenHub 广州入口使用 `hy3` 时，真实
请求曾收到字符串业务码 `429006`（上游服务繁忙或容量限流），响应没有
`Retry-After`。该次运行的脱敏日志如下：

```text
Transient HTTP 429; attempt 2/4 in 0.255s
Transient HTTP 429; attempt 3/4 in 0.538s
Transient HTTP 429; attempt 4/4 in 1.516s
{
  "model": "hy3",
  "finish_reason": "stop",
  "message": {
    "reasoning_content": null,
    "content": "指数退避是一种在重试失败操作（如网络请求）时，每次将等待时间按指数倍递增以避免系统过载和冲突的策略。"
  },
  "usage": {"completion_tokens": 31, "prompt_tokens": 22, "total_tokens": 53}
}
```

之后两次复跑都在第一次请求成功，符合临时错误会自行恢复的特点。jitter 和模型文本
每次都可能不同。若持续收到 `429002/429003/429004/429005`，应检查
RPM/TPM/TPD/并发配置，而不是不断增加重试。

## 容易踩坑

- 不要同时开启 SDK 自动重试和应用重试，否则尝试次数会成倍增长。
- 欠费或额度耗尽不是临时错误，重试不会解决。
- 日志不要打印异常 body、headers、request ID 或 Key。本示例只记录状态类别、
  下一次 attempt 和等待时长。
