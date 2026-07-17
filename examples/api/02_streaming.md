# 02 Streaming：流式请求与逐 chunk 解析

源码：[`02_streaming.py`](02_streaming.py)

## 运行

```bash
python 02_streaming.py
```

## 完整请求

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "用 150 字以内解释流式输出适合什么场景。"}
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
    stream=True,
    stream_options={"include_usage": True},
    extra_body={"thinking": {"type": "disabled"}},
)
```

## 完整响应解析

流式响应不是一个完整对象，而是一系列 `chat.completion.chunk`。脚本会：

1. 遍历每个 chunk；
2. 在 `choices` 非空时读取 `delta.content`；
3. 同时兼容扩展字段 `delta.reasoning_content`；
4. 保存最后出现的 `finish_reason`；
5. 处理 `choices=[]`、只携带 `usage` 的尾包；
6. 拼接并返回完整正文和思考内容。

```python
for chunk in stream:
    if chunk.usage:
        usage = chunk.usage.model_dump()
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    if delta.content:
        content_parts.append(delta.content)
```

不能直接假设每个 chunk 都有 `choices[0]`，否则开启 `include_usage` 后可能在尾包报 `IndexError`。

## 示例输出

```text
streamed content:
流式输出适合聊天界面、代码生成和长文本创作……

parsed response:
{
  "id": "chatcmpl-...",
  "model": "hy3",
  "content": "流式输出适合聊天界面……",
  "reasoning_content": null,
  "finish_reason": "stop",
  "usage": {"prompt_tokens": 25, "completion_tokens": 82, "total_tokens": 107},
  "chunk_count": 19
}
```

示例中的 ID、Token 数和 chunk 数是结构示意。
