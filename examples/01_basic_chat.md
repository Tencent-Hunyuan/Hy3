# Example 1: Basic Chat — Single-turn & Multi-turn

## 请求

### 单轮

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "解释一下什么是量子计算，用一句话。"},
    ],
    temperature=0.7,
    max_tokens=256,
)
```

### 响应

```
id: chatcmpl-xxxxx
model: hy3
usage: CompletionUsage(completion_tokens=32, prompt_tokens=18, total_tokens=50)
finish_reason: stop
```

- `finish_reason`: `stop` / `length` / `tool_calls`

### 多轮

将历史消息追加到 `messages` 数组：

```python
messages = [
    {"role": "user", "content": "我最喜欢的动物是企鹅。"},
]
messages.append({"role": "assistant", "content": reply1})
messages.append({"role": "user", "content": "为什么？它有什么特别之处？"})
```

## 示例输出

```
============================================================
1. Single-turn Chat
============================================================
User: 解释一下什么是量子计算，用一句话。
Assistant: 量子计算是一种利用量子力学原理（如叠加和纠缠）来处理信息的计算范式。

--- Response 完整结构 ---
id: chatcmpl-xxx1
model: hy3
usage: CompletionUsage(completion_tokens=27, prompt_tokens=18, total_tokens=45)
finish_reason: stop

============================================================
2. Multi-turn Chat
============================================================
User: 我最喜欢的动物是企鹅。
Assistant: 企鹅是非常可爱的鸟类！它们虽然不会飞，但游泳技术一流。

User: 为什么？它有什么特别之处？
Assistant: 企鹅有厚厚的脂肪层和密集的羽毛来抵御严寒，还能潜入深海捕食。

User: 用三个词描述企鹅。
Assistant: 耐寒、游泳健将、绅士。
```
