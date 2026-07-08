<p align="left">
    <a href="../02_streaming.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# 示例 02：流式输出

本示例演示 `stream=True` 以及逐 chunk 解析响应。

> 相关文档：[示例索引](./README.md) | [API 快速开始](../../quickstart_CN.md)

## 运行

```bash
python examples/zh-cn/02_streaming.py
```

## 完整请求

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

等价的 HTTP 请求体：

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

## 响应解析

```python
for chunk in stream:
    choice = chunk.choices[0]
    delta = choice.delta
    content = getattr(delta, "content", None)
    if content:
        print(content, end="", flush=True)
    if choice.finish_reason:
        print("结束原因:", choice.finish_reason)
```

## 示例输出

```text
assistant: 1. 聊天机器人：让用户更快看到响应开始。
2. 代码生成：边生成边阅读，降低等待感。
3. 长文总结：可以持续刷新 UI。
4. Agent 执行：便于展示中间进度。
5. 在线客服：改善首字反馈体验。
结束原因: stop
chunk 数: 87
总字符数: 143
```
