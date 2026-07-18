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

## 示例输出（2026-07-18 TokenHub 实测，脱敏）

```text
=== Chunk parse (delta.content) ===
Hy3 适合处理复杂的多步骤推理任务，比如数学证明、代码生成与逻辑分析等需要深度思考的场景。
它擅长在对话中保持长期上下文一致性，适用于需要连续交互的咨询、写作辅助或项目管理等任务。
同时，Hy3 也适合用于知识整合与内容创作，能高效将分散信息转化为结构化的摘要、报告或教学材料。

chunks_seen≈53 finish_reason=stop
usage: prompt=25 completion=84 total=109
```

原始 SSE 形态示意：

```text
data: {"id":"REPLACED_ID","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"}}]}
data: {"id":"REPLACED_ID","choices":[{"delta":{"content":"Hy3"}}]}
data: {"id":"REPLACED_ID","choices":[{"delta":{"content":" 适合"},"finish_reason":null}]}
...
data: {"id":"REPLACED_ID","choices":[],"usage":{"prompt_tokens":25,"completion_tokens":84,"total_tokens":109}}
data: [DONE]
```
