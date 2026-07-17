# 02 Streaming — 流式请求与逐 chunk 解析

演示 `stream=true` 的 SSE 流式输出，以及如何拼接 `delta.content`。

## 运行

```bash
cd examples/api
python 02_streaming/main.py
```

## 完整请求

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "用三句话介绍 Hy3 适合做什么。"}
  ],
  "temperature": 0.9,
  "top_p": 1.0,
  "max_tokens": 512,
  "stream": true,
  "stream_options": {"include_usage": true}
}
```

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "用三句话介绍 Hy3 适合做什么。"}],
    stream=True,
    stream_options={"include_usage": True},
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
    if chunk.usage:
        print("\nusage:", chunk.usage)
```

## 响应解析

流式响应是多行 `data: {...}`，直到 `data: [DONE]`。

| 阶段 | 字段 | 含义 |
|---|---|---|
| 首包 | `choices[0].delta.role` | 常为 `assistant` |
| 中间包 | `choices[0].delta.content` | 增量文本，可能为空 |
| 结束包 | `choices[0].finish_reason` | 如 `stop` |
| 可选尾包 | `usage` | 开启 `include_usage` 后出现；此时 `choices` 可能为空 |

拼装最终答案：

```python
text = "".join(
    (c.choices[0].delta.content or "")
    for c in stream_chunks
    if c.choices
)
```

## 示例输出（脱敏）

```text
=== Chunk parse (delta.content) ===
Hy3 适合编程助手与 Agent 工作流。它在长上下文理解上表现稳定。复杂推理任务可开启思考模式。

chunks_seen≈42 finish_reason=stop
usage: prompt=22 completion=48 total=70
assembled_content: Hy3 适合编程助手与 Agent 工作流。它在长上下文理解上表现稳定。复杂推理任务可开启思考模式。
```

原始 SSE 形态示意：

```text
data: {"id":"REPLACED_ID","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"}}]}
data: {"id":"REPLACED_ID","choices":[{"delta":{"content":"Hy3"}}]}
data: {"id":"REPLACED_ID","choices":[{"delta":{"content":" 适合"},"finish_reason":null}]}
...
data: {"id":"REPLACED_ID","choices":[],"usage":{"prompt_tokens":22,"completion_tokens":48,"total_tokens":70}}
data: [DONE]
```
