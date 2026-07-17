# 01 Basic Chat：单轮与多轮对话

源码：[`01_basic_chat.py`](01_basic_chat.py)

## 运行

```bash
python 01_basic_chat.py
```

## 完整请求

单轮和多轮调用都使用同一请求函数：

```python
response = client.chat.completions.create(
    model=model,
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
    extra_body={"thinking": {"type": "disabled"}},
)
```

多轮对话不会由 API 自动保存历史。客户端必须追加上一轮 assistant 回复和新的 user 消息：

```python
history.append({"role": "assistant", "content": first_reply})
history.append({"role": "user", "content": "把第二步展开成 7 天安排。"})
```

## 完整响应解析

脚本检查 `choices`，并解析：

- `response.id`：请求响应 ID；
- `response.model`：实际模型；
- `choices[0].message.content`：回复正文；
- `choices[0].finish_reason`：`stop`、`length` 或 `tool_calls`；
- `response.usage`：输入、输出和总 Token 数。

关键代码：

```python
choice = response.choices[0]
content = choice.message.content
finish_reason = choice.finish_reason
usage = response.usage.model_dump() if response.usage else None
```

## 示例输出

下面是字段结构示意，实际文本和 Token 数会变化：

```text
=== Single-turn chat ===
assistant: 1. 混合专家模型由多个专家网络组成……
finish_reason: stop
usage: {'prompt_tokens': 24, 'completion_tokens': 98, 'total_tokens': 122}

=== Multi-turn chat ===
round 1 assistant: 第一步学习语法基础……
round 2 assistant: 第 1 天练习列表和字典……
finish_reason: stop
usage: {'prompt_tokens': 156, 'completion_tokens': 230, 'total_tokens': 386}
```
