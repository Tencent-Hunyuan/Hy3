# Error Handling & Retry（超时 / 限流 / 网络错误）

## 目标

本示例演示如何区分超时、429 限流、网络连接错误和 5xx 服务端错误，并通过带随机抖动的指数退避进行有限次数重试。

## 前置条件

- Python 3.10+
- OpenAI Python SDK `openai>=1.0.0`，环境变量加载库 `python-dotenv>=1.0.0`
- 必需环境变量：`HY3_BASE_URL`、`HY3_API_KEY`、`HY3_MODEL`
- 可选环境变量：`HY3_TIMEOUT_SECONDS=30`、`HY3_MAX_RETRIES=3`、`HY3_RETRY_BASE_SECONDS=1`、`HY3_RETRY_MAX_SECONDS=30`
- 模型能力要求：仅需支持非流式 Chat Completions；错误类型主要由 SDK、网络、服务端和网关决定

安装依赖：

```bash
python -m pip install "openai>=1.0.0" "python-dotenv>=1.0.0"
```

## 完整请求

示例把 SDK 内置重试设为 `0`，以便清楚展示调用方自己的重试与退避逻辑。生产代码应避免同时叠加多层未知次数的重试。

```python
client = OpenAI(
    base_url=BASE_URL,
    api_key=API_KEY,
    timeout=TIMEOUT_SECONDS,
    max_retries=0,
)

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "请用一句话解释什么是指数退避。"}
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)
```

## 完整 Response 解析

脚本捕获并分类以下异常：

- `APITimeoutError`：连接、写入、读取或连接池等待超时。
- `RateLimitError`：服务端或网关返回 HTTP 429；优先读取数字形式的 `Retry-After`。
- `APIConnectionError`：DNS、连接拒绝、连接重置等网络错误。
- `APIStatusError`：仅对 HTTP 5xx 重试；400、401、403、404 等非暂时性错误直接抛出。

```python
for attempt in range(MAX_RETRIES + 1):
    try:
        response = client.chat.completions.create(...)
        break
    except (RateLimitError, APITimeoutError, APIConnectionError, APIStatusError) as exc:
        category = retry_category(exc)
        if category is None or attempt >= MAX_RETRIES:
            raise
        delay = compute_delay(attempt, exc)
        time.sleep(delay)
```

成功后会解析响应 ID、模型、全部 choices、正文、结束原因和 Token 用量。退避公式为 `base * 2^retry_index + jitter`，并受 `HY3_RETRY_MAX_SECONDS` 限制；429 的数字 `Retry-After` 优先。

## 运行方式

在 `quickstart/` 目录执行：

```bash
python examples/06_error_handling/error_handling.py
```

可将 `HY3_BASE_URL` 临时设为不可访问地址以观察网络错误；不要在生产服务上故意制造高并发来测试 429。

## 示例输出

```text
第 1 次请求失败（网络错误），1.08s 后进行第 1 次重试
第 2 次请求失败（限流），2.00s 后进行第 2 次重试

=== 请求成功 ===
id=chatcmpl-retry-example
model=hy3
choice[0].finish_reason=stop
choice[0].content=指数退避是在连续失败后逐步延长重试等待时间的策略。
usage: prompt=19, completion=24, total=43
```

实际错误顺序、等待时间、ID 和 Token 数会随环境变化。
