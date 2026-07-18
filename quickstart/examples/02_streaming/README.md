# Streaming（流式请求 + 逐 Chunk 解析）

## 目标

本示例演示如何开启 Chat Completions 流式响应，逐个解析 `ChatCompletionChunk`，并把多个 `delta.content` 重建为完整回答。

## 前置条件

- Python 3.10+
- OpenAI Python SDK `openai>=1.0.0`，环境变量加载库 `python-dotenv>=1.0.0`
- 环境变量：`HY3_BASE_URL`、`HY3_API_KEY`、`HY3_MODEL`；可从 `quickstart/.env.example` 复制为 `quickstart/.env`
- 模型能力要求：部署服务支持 Chat Completions 流式输出；如不支持 `stream_options.include_usage`，可删除该参数，正文流不受影响

安装依赖：

```bash
python -m pip install "openai>=1.0.0" "python-dotenv>=1.0.0"
```

## 完整请求

```python
stream = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "user",
            "content": "请用三句话说明流式响应适合什么场景。",
        }
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    stream=True,
    stream_options={"include_usage": True},
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)
```

## 完整 Response 解析

流式响应不是一个完整 message，而是一系列 chunk。首个 chunk 可能只包含 `role`，中间 chunk 才包含正文，最后还可能有 `finish_reason` 或只有 `usage`、没有 `choices`，因此不能固定读取 `chunk.choices[0]`。

```python
text_by_choice = {}
finish_reasons = {}
usage = None

for chunk in stream:
    usage = getattr(chunk, "usage", None) or usage
    for choice in chunk.choices:
        text_by_choice.setdefault(choice.index, [])
        content = getattr(choice.delta, "content", None)
        if content:
            text_by_choice[choice.index].append(content)
        if choice.finish_reason:
            finish_reasons[choice.index] = choice.finish_reason

full_text = "".join(text_by_choice[0])
print(full_text, finish_reasons.get(0), usage)
```

脚本还会逐 chunk 打印 `role`、`content`、`reasoning_content` 和 `finish_reason`，便于观察协议实际返回内容。

## 运行方式

在 `quickstart/` 目录执行：

```bash
python examples/02_streaming/streaming.py
```

## 示例输出

```text
chunk=1, choice=0, role='assistant', content=None, finish_reason=None
chunk=2, choice=0, role=None, content='流式', finish_reason=None
chunk=3, choice=0, role=None, content='响应适合需要快速反馈的交互场景。', finish_reason=None
chunk=4, choice=0, role=None, content=None, finish_reason='stop'

=== 重建后的完整响应 ===
id=chatcmpl-example
model=hy3
choice[0].finish_reason=stop
choice[0].content=流式响应适合需要快速反馈的交互场景。它能降低用户感知等待时间。客户端需逐块拼接输出。
usage: prompt=22, completion=38, total=60
```

Chunk 边界、ID、正文和 Token 数均为示意，实际结果由服务端决定。
