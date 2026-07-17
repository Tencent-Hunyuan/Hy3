# 01 基础对话 / Basic Chat

[中文](#中文) | [English](#english)

---

## 中文

本示例展示如何使用 Hy3 API 进行基础对话，包括**单轮对话**和**多轮对话**。

### 单轮对话

最简单的场景：发送一条消息，获取模型回复。

#### 请求

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "用一句话解释什么是大语言模型。"},
    ],
    temperature=0.9,
    top_p=1.0,
)
```

#### 响应解析

```python
# 获取回复内容
content = response.choices[0].message.content
print(content)

# 获取使用统计
print(f"Prompt tokens: {response.usage.prompt_tokens}")
print(f"Completion tokens: {response.usage.completion_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")

# 获取结束原因
print(f"Finish reason: {response.choices[0].finish_reason}")  # "stop" 表示正常结束
```

#### 示例输出

```
大语言模型（LLM）是基于 Transformer 架构、在海量文本上训练的深度学习模型，能够理解和生成自然语言，执行问答、翻译、写作、编程等多种任务。

Prompt tokens: 28
Completion tokens: 65
Total tokens: 93
Finish reason: stop
```

---

### 多轮对话

将历史对话消息传入 `messages` 列表，模型会基于上下文进行回复。

#### 请求

```python
messages = [
    {"role": "system", "content": "你是一位友好的Python编程助手。"},
    {"role": "user", "content": "Python的列表和元组有什么区别？"},
]

# 第一轮
response1 = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
)

# 将助手回复加入历史
messages.append({"role": "assistant", "content": response1.choices[0].message.content})

# 第二轮：基于上下文追问
messages.append({"role": "user", "content": "那在什么场景下应该优先使用元组？"})

response2 = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
)
print(response2.choices[0].message.content)
```

#### 响应解析

多轮对话的响应格式与单轮完全一致，关键在于维护 `messages` 列表：

```python
# 每次请求后，将助手回复追加到 messages
messages.append({
    "role": "assistant",
    "content": response.choices[0].message.content,
})

# 每次请求前，追加新的用户消息
messages.append({
    "role": "user",
    "content": "新的问题...",
})
```

#### 示例输出

```
在以下场景中建议优先使用元组：
1. 数据不应被修改时（如配置项、数据库记录）——元组的不可变性提供安全保障
2. 作为字典的 key——只有可哈希的不可变类型才能作为字典键
3. 函数返回多个值时——`return x, y` 自动返回元组
4. 性能敏感场景——元组的内存占用略低于列表，创建速度更快
```

---

## English

This example shows how to use the Hy3 API for basic chat, including **single-turn** and **multi-turn** conversations.

### Single-Turn Chat

The simplest case: send one message and get a response.

#### Request

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "Explain what a large language model is in one sentence."},
    ],
    temperature=0.9,
    top_p=1.0,
)
```

#### Response Parsing

```python
content = response.choices[0].message.content
print(content)

print(f"Prompt tokens: {response.usage.prompt_tokens}")
print(f"Completion tokens: {response.usage.completion_tokens}")
print(f"Total tokens: {response.usage.total_tokens}")
print(f"Finish reason: {response.choices[0].finish_reason}")  # "stop" = completed normally
```

#### Example Output

```
A large language model (LLM) is a deep learning model based on the Transformer architecture,
trained on massive text corpora, capable of understanding and generating natural language to
perform tasks like Q&A, translation, writing, and coding.

Prompt tokens: 26
Completion tokens: 58
Total tokens: 84
Finish reason: stop
```

---

### Multi-Turn Chat

Pass the conversation history in the `messages` list to maintain context.

#### Request

```python
messages = [
    {"role": "system", "content": "You are a friendly Python programming assistant."},
    {"role": "user", "content": "What's the difference between lists and tuples in Python?"},
]

# First turn
response1 = client.chat.completions.create(
    model="hy3", messages=messages, temperature=0.9, top_p=1.0,
)

# Append assistant reply to history
messages.append({"role": "assistant", "content": response1.choices[0].message.content})

# Second turn: follow-up question
messages.append({"role": "user", "content": "When should I prefer tuples over lists?"})

response2 = client.chat.completions.create(
    model="hy3", messages=messages, temperature=0.9, top_p=1.0,
)
print(response2.choices[0].message.content)
```

#### Example Output

```
Prefer tuples in these scenarios:
1. When data should not be modified (e.g., config items, DB records) — immutability provides safety
2. As dictionary keys — only hashable immutable types can be dict keys
3. Returning multiple values from functions — `return x, y` automatically returns a tuple
4. Performance-sensitive code — tuples use slightly less memory and are faster to create
```
