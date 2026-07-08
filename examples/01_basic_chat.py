"""
Example 1: Basic Chat — Single-turn & Multi-turn

Prerequisites:
  - Hy3 server running on port 8000
  - pip install openai
"""

from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

# 1. 单轮对话
print("=" * 60)
print("1. Single-turn Chat")
print("=" * 60)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "解释一下什么是量子计算，用一句话。"},
    ],
    temperature=0.7,
    max_tokens=256,
)
single_reply = response.choices[0].message.content
print(f"User: 解释一下什么是量子计算，用一句话。")
print(f"Assistant: {single_reply}")

print("\n--- Response 完整结构 ---")
print(f"id: {response.id}")
print(f"model: {response.model}")
print(f"usage: {response.usage}")
print(f"finish_reason: {response.choices[0].finish_reason}")

# 2. 多轮对话
print("\n" + "=" * 60)
print("2. Multi-turn Chat")
print("=" * 60)

messages = [
    {"role": "user", "content": "我最喜欢的动物是企鹅。"},
]

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    max_tokens=256,
)
reply1 = response.choices[0].message.content
print(f"User: 我最喜欢的动物是企鹅。")
print(f"Assistant: {reply1}")

messages.append({"role": "assistant", "content": reply1})
messages.append({"role": "user", "content": "为什么？它有什么特别之处？"})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    max_tokens=256,
)
reply2 = response.choices[0].message.content
print(f"\nUser: 为什么？它有什么特别之处？")
print(f"Assistant: {reply2}")

messages.append({"role": "assistant", "content": reply2})
messages.append({"role": "user", "content": "用三个词描述企鹅。"})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    max_tokens=256,
)
reply3 = response.choices[0].message.content
print(f"\nUser: 用三个词描述企鹅。")
print(f"Assistant: {reply3}")
