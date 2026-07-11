# Example 1: Basic Chat（基础对话）

## 1.目标

展示单轮和多轮对话的基本用法，理解请求和响应结构。

## 2.单轮对话

单轮对话是最简单的调用方式，只需发送一条用户消息即可。

### 2.1请求示例

#### cURL

```bash
curl -X POST 'https://tokenhub.tencentmaas.com/v1/chat/completions' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好，请简单介绍一下你自己。"}
    ],
    "stream": false,
    "temperature": 0.9
  }'
```

#### Python

```python
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好，请简单介绍一下你自己。"},
    ],
    temperature=0.9,
)

print("=== 响应内容 ===")
print("ID:", response.id)
print("模型:", response.model)
print("回答:", response.choices[0].message.content)
print("结束原因:", response.choices[0].finish_reason)
print("\n=== Token 使用 ===")
print(f"输入: {response.usage.prompt_tokens} tokens")
print(f"输出: {response.usage.completion_tokens} tokens")
print(f"总计: {response.usage.total_tokens} tokens")
```

### 2.2响应解析

```json
{
  "id": "REPLACED_ID",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1775146513,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是混元，是由腾讯开发的大模型。我的主要功能是基础信息处理与逻辑响应，比如回答各种问题、解决问题、学习新知识、创造内容，还能陪你闲聊呢。如果你有任何问题都可以随时问我哦。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 22,
    "completion_tokens": 50,
    "total_tokens": 72,
    "prompt_tokens_details": {"cached_tokens": 0},
    "completion_tokens_details": {"reasoning_tokens": 0}
  }
}
```

**响应字段说明：**

| 字段 | 说明 |
|------|------|
| `id` | 请求唯一标识 |
| `object` | 对象类型，固定为 `chat.completion` |
| `model` | 实际使用的模型名称 |
| `created` | 创建时间（Unix 时间戳） |
| `choices[0].message.role` | 角色，这里是 `assistant` |
| `choices[0].message.content` | 模型的回答内容 |
| `choices[0].finish_reason` | 结束原因：`stop`（正常结束）、`length`（达到最大长度）、`tool_calls`（需要调用工具） |
| `usage.prompt_tokens` | 输入 token 数 |
| `usage.completion_tokens` | 输出 token 数 |
| `usage.total_tokens` | 总 token 数 |

### 2.3示例输出

```
=== 响应内容 ===
ID: REPLACED_ID
模型: hy3
回答: 你好！我是混元，是由腾讯开发的大模型。我的主要功能是基础信息处理与逻辑响应，比如回答各种问题、解决问题、学习新知识、创造内容，还能陪你闲聊呢。如果你有任何问题都可以随时问我哦。
结束原因: stop

=== Token 使用 ===
输入: 22 tokens
输出: 50 tokens
总计: 72 tokens
```

## 3多轮对话

多轮对话需要维护完整的对话历史，将之前的对话消息依次传递给模型。

### 3.1请求示例

#### Python

```python
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

messages = []

user_msg = "你好，请简单介绍一下你自己。"
messages.append({"role": "user", "content": user_msg})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
)

assistant_reply = response.choices[0].message.content
messages.append({"role": "assistant", "content": assistant_reply})
print(f"用户: {user_msg}")
print(f"助手: {assistant_reply}")
print()

user_msg = "你擅长什么？"
messages.append({"role": "user", "content": user_msg})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
)

assistant_reply = response.choices[0].message.content
messages.append({"role": "assistant", "content": assistant_reply})
print(f"用户: {user_msg}")
print(f"助手: {assistant_reply}")
print()

user_msg = "那你能帮我写一段 Python 代码吗？"
messages.append({"role": "user", "content": user_msg})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
)

assistant_reply = response.choices[0].message.content
print(f"用户: {user_msg}")
print(f"助手: {assistant_reply}")
```

### 3.2响应解析

多轮对话的响应结构与单轮对话相同，关键在于 `messages` 数组包含完整的对话历史：

```json
[
  {"role": "user", "content": "你好，请简单介绍一下你自己。"},
  {"role": "assistant", "content": "你好！我是混元..."},
  {"role": "user", "content": "你擅长什么？"},
  {"role": "assistant", "content": "我擅长..."},
  {"role": "user", "content": "那你能帮我写一段 Python 代码吗？"}
]
```

### 3.3示例输出

```
用户: 你好，请简单介绍一下你自己。
助手: 你好！我是混元，是由腾讯开发的大模型。我的主要功能是基础信息处理与逻辑响应，比如回答各种问题、解决问题、学习新知识、创造内容，还能陪你闲聊呢。如果你有任何问题都可以随时问我哦。

用户: 你擅长什么？
助手: 我擅长多种任务，包括：\n\n1. **自然语言处理**：回答问题、文本生成、翻译、摘要等\n2. **代码开发**：编写、解释和调试代码，支持多种编程语言\n3. **逻辑推理**：解决数学问题、分析复杂问题\n4. **创意创作**：写文章、故事、诗歌等\n5. **实用工具**：提供建议、帮助制定计划等\n\n有什么具体需要帮忙的吗？

用户: 那你能帮我写一段 Python 代码吗？
助手: 当然可以！请问你需要什么功能的代码呢？比如：\n\n- 数据处理（Pandas/Numpy）\n- Web 开发（Flask/FastAPI）\n- 机器学习（Scikit-learn）\n- 自动化脚本\n- 其他特定功能\n\n请告诉我你的需求，我会为你编写合适的代码。
```

## 关键点

1. **消息顺序**：必须按照 `user → assistant → user → ...` 的顺序排列
2. **角色类型**：`system`（系统提示）、`user`（用户）、`assistant`（助手）、`tool`（工具返回）
3. **上下文管理**：多轮对话需要将历史消息全部传递给模型
4. **Token 消耗**：输入消息越多，`prompt_tokens` 越高，费用也越高

正式测试代码请参考01_basic_chat.ipynb/01_basic_chat.py