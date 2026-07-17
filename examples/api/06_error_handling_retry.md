# 06 — Error handling and retry

目标：演示 Hosted API 的显式、有限重试。SDK 自带重试被关闭，所有决策由
[common.py](common.py) 的 `call_with_retry` 可测试地完成。完整调用见
[06_error_handling_retry.py](06_error_handling_retry.py)。

## 完整请求与策略

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

## 运行与真实输出

```powershell
python examples/api/06_error_handling_retry.py
```

正常调用可能不会触发重试；离线测试用 fake 401/429/502/503/504、timeout 和
connection error 覆盖分支。2026-07-17 的 TokenHub 广州 `hy3` live 会话实际命中
字符串业务码 `429006`（官方定义为上游服务繁忙或容量限流），且响应未带
`Retry-After`。同一次真实运行的公开日志如下：

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

之后的两次 live 复跑都首试成功，这正是临时错误的预期特征；jitter 随机值与模型
文本也会变化。若持续收到 `429002/429003/429004/429005`，应检查
RPM/TPM/TPD/并发配置，而不是增加无限重试。

重试日志只显示状态类别、下一次 attempt 和等待时长，不打印异常 body、headers、
request ID 或 Key。常见错误是同时开启 SDK 自动重试与应用重试，导致尝试次数成倍
增长，或把欠费/额度耗尽当成临时 429 无限重试。
