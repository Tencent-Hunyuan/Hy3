<p align="left">
    <a href="./zh-cn/02_streaming.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Example 02: Streaming

This example demonstrates `stream=True` and chunk-by-chunk parsing.

> Related: [Examples Index](./README.md) | [API Quickstart](../quickstart.md)

## Run

```bash
python examples/02_streaming.py
```

## Full request

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "用 5 个要点解释流式输出适合哪些产品场景。"}],
    temperature=0.7,
    top_p=1.0,
    max_tokens=500,
    stream=True,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

Equivalent HTTP body:

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "用 5 个要点解释流式输出适合哪些产品场景。"}
  ],
  "temperature": 0.7,
  "top_p": 1.0,
  "max_tokens": 500,
  "stream": true,
  "chat_template_kwargs": {"reasoning_effort": "no_think"}
}
```

## Response parsing

```python
for chunk in stream:
    choice = chunk.choices[0]
    delta = choice.delta
    content = getattr(delta, "content", None)
    if content:
        print(content, end="", flush=True)
    if choice.finish_reason:
        print("finish_reason:", choice.finish_reason)
```

## Sample output

```text
assistant: 1. 聊天机器人：让用户更快看到响应开始。
2. 代码生成：边生成边阅读，降低等待感。
3. 长文总结：可以持续刷新 UI。
4. Agent 执行：便于展示中间进度。
5. 在线客服：改善首字反馈体验。
finish_reason: stop
chunks: 87
total_chars: 143
```
