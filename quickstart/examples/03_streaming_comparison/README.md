# Non-streaming vs Streaming（首个内容时延 / 总耗时）

## 目标

本示例使用相同提示词和生成参数，对比非流式与流式请求的客户端首个可见内容时延和总耗时。

## 前置条件

- Python 3.10+
- OpenAI Python SDK `openai>=1.0.0`，环境变量加载库 `python-dotenv>=1.0.0`
- 环境变量：`HY3_BASE_URL`、`HY3_API_KEY`、`HY3_MODEL`；可从 `quickstart/.env.example` 复制为 `quickstart/.env`
- 模型能力要求：部署服务同时支持非流式与流式 Chat Completions

安装依赖：

```bash
python -m pip install "openai>=1.0.0" "python-dotenv>=1.0.0"
```

## 完整请求

```python
common = {
    "model": MODEL,
    "messages": [
        {"role": "user", "content": "请用五个要点解释大语言模型的流式输出。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 128,
    "extra_body": {
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
}

non_streaming_response = client.chat.completions.create(**common)
streaming_response = client.chat.completions.create(
    **common,
    stream=True,
    stream_options={"include_usage": True},
)
```

## 完整 Response 解析

- 非流式：解析响应的全部 `choices`、正文、`finish_reason` 和 `usage`。
- 流式：遍历所有 chunk，记录第一个非空 `delta.content` 到达时间，拼接每个 choice 的完整正文，并解析最终 `finish_reason` 与可选 `usage`。
- 非流式 API 在整条响应完成前不会向客户端暴露 token，所以示例报告的是“首个可见内容时延”，其值等于非流式总耗时；它不是真实的服务端首 token 生成时刻。

```python
started_at = time.perf_counter()
first_content_seconds = None
parts = []

for chunk in streaming_response:
    for choice in chunk.choices:
        content = getattr(choice.delta, "content", None)
        if content:
            if first_content_seconds is None:
                first_content_seconds = time.perf_counter() - started_at
            parts.append(content)

total_seconds = time.perf_counter() - started_at
full_text = "".join(parts)
```

这是一组客户端单次观测值，会受到网络、排队、缓存、预热和生成长度影响。严谨压测应多次运行、交替请求顺序并统计分位数。

## 运行方式

在 `quickstart/` 目录执行：

```bash
python examples/03_streaming_comparison/streaming_comparison.py
```

## 示例输出

```text
=== 非流式 完整解析 ===
id=chatcmpl-non-stream
model=hy3
choice[0].finish_reason=stop
choice[0].content=1. 更快显示首段内容……
usage={'prompt_tokens': 20, 'completion_tokens': 80, 'total_tokens': 100}

=== 流式 完整解析 ===
id=chatcmpl-stream
model=hy3
chunk_count=26
choice[0].finish_reason=stop
choice[0].content=1. 更快显示首段内容……
usage={'prompt_tokens': 20, 'completion_tokens': 80, 'total_tokens': 100}

=== 时延对比（客户端观测值） ===
非流式: 首个可见内容=2.481s, 总耗时=2.481s
流式:   首个内容 chunk=0.364s, 总耗时=2.593s
```

示例时延不代表 Hy3 的固定性能或服务 SLA，应以目标部署环境中的实际压测为准。
