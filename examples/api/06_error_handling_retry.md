# 06 错误处理与重试

这个示例只重试临时错误，并限制尝试次数和总等待时间。SDK 自带重试保持关闭，所有
重试都由业务代码统一处理。完整代码见
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
| 其他状态 | 否 | 原样向上抛出，由调用方处理。 |

`Retry-After` 支持秒数和 HTTP date；脚本会将两种格式解析为等待秒数。jitter 只用于
指数退避。若下一次等待会超过 `max_total_wait`，抛出 `RetryBudgetExceeded`。达到
`max_attempts` 后抛出最后一个原始错误并结束循环。

## 运行结果

```powershell
python examples/api/06_error_handling_retry.py
```

正常调用通常一次成功。离线测试使用模拟的 401/429/502/503/504、timeout 和
connection error 覆盖各分支。2026-07-17 在 TokenHub 广州入口使用 `hy3` 时，真实
请求曾收到字符串业务码 `429006`（上游服务繁忙或容量限流），响应缺少
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

之后两次复跑都在第一次请求成功。jitter 和模型文本每次都可能变化。持续收到
`429002/429003/429004/429005` 时，应检查
RPM/TPM/TPD/并发配置；增加重试只会延长等待。

## 容易踩坑

- 只保留一层重试。本示例关闭 SDK 自动重试，由应用统一控制尝试次数。
- 欠费或额度耗尽需要充值或调整配额。
- 日志只记录状态类别、下一次 attempt 和等待时长；异常 body、headers、request ID
  和 Key 全部省略。
