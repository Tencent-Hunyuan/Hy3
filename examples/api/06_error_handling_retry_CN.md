# 06 错误处理与重试

[English](06_error_handling_retry.md) · [索引](README_CN.md) · [脚本](06_error_handling_retry.py)

## 用途

在 OpenAI 兼容请求外增加可见、有界的应用层重试策略。[`06_error_handling_retry.py`](06_error_handling_retry.py)还提供不需要 API 配置或网络的确定性 `--simulate` 模式。

## 配置

实时调用需要配置 `examples/api/.env`。脚本以 `max_retries=0` 创建 SDK client，因此只有应用层策略负责重试。默认最多四次总尝试，指数 jitter 的 `base_delay=0.5`、`max_delay=8.0`。

`--simulate` 模式会直接跳过环境加载和 client 创建。

## 完整请求

实时 client 与完整请求为：

```python
client = create_client(config, max_retries=0)

client.chat.completions.create(
    model=config.model,
    messages=[
        {
            "role": "user",
            "content": "Give one sentence about reliable API clients.",
        }
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    extra_body=reasoning_extra_body(config, "no_think"),
)
```

该 operation 被传给：

```python
call_with_retry(operation, on_retry=print_retry)
```

默认策略重试 SDK connection/timeout，以及状态码 408、409、429 或 5xx。其他状态会立即重新抛出。

## 响应解析

每次捕获 `Exception` 后，`call_with_retry` 会：

1. 检查错误是否可重试，以及是否还有剩余 attempt。
2. 存在时读取非负且有限的数值型 `Retry-After` 秒数。
3. 否则计算 `min(max_delay, base_delay * 2 ** (attempt - 1))`，再乘以 `random.random()` 得到 full jitter。
4. 调用 `on_retry(next_attempt, max_attempts, delay, error)`，然后 sleep。
5. 最后一次失败直接重新抛出，不再 callback 或 sleep。

成功后，`summarize_completion` 把响应解析为 content、可选 reasoning/details、finish reason 和 usage。callback 或 sleep 自身异常不会被吞掉；`KeyboardInterrupt` 等 `BaseException` 不在重试捕获范围内。

## 运行

确定性离线模拟：

```bash
python examples/api/06_error_handling_retry.py --simulate
```

使用已配置后端的实时请求：

```bash
python examples/api/06_error_handling_retry.py
```

## 示例输出

**已验证的实时观测**

```text
后端：OpenRouter
请求模型：tencent/hy3:free
解析模型：tencent/hy3-20260706:free
观测日期：2026-07-11

Retry 2/4 in 0.00s after APIConnectionError
Retry 3/4 in 0.25s after APIConnectionError
Retry 4/4 in 1.73s after APIConnectionError
content：关于可靠 API client 的一句话
usage.total_tokens：49
```

这只是一次实时瞬时恢复观测，不承诺精确的失败序列和 jitter 延迟能够复现。

**确定性离线模拟**

```text
Retry 2/4 in 0.00s after RateLimitError
rate_limit: recovered
Retry 2/4 in 0.00s after APITimeoutError
timeout: recovered
Retry 2/4 in 0.00s after APIConnectionError
connection: recovered
```

确定性 `--simulate` 模式为每个场景注入一个错误，禁用真实 sleep，使用确定性 jitter，然后返回 `recovered`。

## 限制与注意事项

- 只解析有限的数值型 Retry-After 秒数；HTTP-date 会回退到 jitter。
- 上述实时 connection-error 序列是观测证据，不是脚本的固定输出。
- Retry-After 不受 `max_delay` 限制；生产策略可按需要再设置上限。
- 默认随机源适合 jitter，不适合密码学。
- 该策略是同步的，会阻塞当前线程。
- 重试非幂等 operation 可能重复副作用；示例请求仅用于演示，生产中应逐个评估 operation。
- 示例不包含 circuit breaker、共享 retry budget、可观测性或线程协调。
- 实时 CLI 依赖进程退出释放 client。
