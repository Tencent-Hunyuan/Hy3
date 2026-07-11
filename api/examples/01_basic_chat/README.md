# Basic chat：单轮与多轮

运行：

```bash
python api/examples/01_basic_chat/basic_chat.py
```
完整请求在 [`basic_chat.py`](basic_chat.py) 中。单轮请求直接传入一条 `user` 消息；多轮请求把第一次返回的完整 assistant message 追加到 `messages`，再追加新的 user 消息。这样会保留角色、文本及可能存在的扩展字段。

非流式响应的完整解析由 `print_response` 完成：读取 `id`、`model`、`role`、`reasoning_content`、`content`、`tool_calls`、`finish_reason` 和 `usage`。请求核心如下：

```python
response = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "用一句话介绍 Hy3。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

示例输出：

```text
=== Single turn ===
id: chatcmpl-a12b
model: hy3
role: assistant
content: Hy3 是腾讯混元开源的高性能大语言模型。
finish_reason: stop
usage: prompt=14, completion=19, total=33

=== Multi turn ===
id: chatcmpl-a12d
model: hy3
role: assistant
content: 例如：evens = [x for x in numbers if x % 2 == 0]
finish_reason: stop
usage: prompt=67, completion=23, total=90
```
