# Streaming：逐 chunk 解析

运行：

```bash
python api/examples/02_streaming/streaming.py
```
完整请求在 [`streaming.py`](streaming.py) 中。设置 `stream=True` 后，SDK 返回迭代器；脚本逐块累积 `delta.content` 和可选的 `delta.reasoning_content`，保存 `finish_reason`，并处理仅含 `usage`、不含 `choices` 的尾包。

```python
stream = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "列出三个学习 Python 的建议。"}],
    stream=True,
    stream_options={"include_usage": True},
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        content_parts.append(chunk.choices[0].delta.content)
```

示例输出（实际 chunk 边界不固定）：

```text
chunk id=chatcmpl-b31
  content='1.'
chunk id=chatcmpl-b31
  content=' 坚持动手练习；'
chunk id=chatcmpl-b31
  content='2. 阅读优秀代码；3. 完成小项目。'
chunk id=chatcmpl-b31

=== Parsed response ===
content: 1. 坚持动手练习；2. 阅读优秀代码；3. 完成小项目。
finish_reason: stop
usage: prompt=15, completion=31, total=46
```
