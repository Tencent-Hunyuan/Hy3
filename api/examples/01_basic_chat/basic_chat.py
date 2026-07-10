"""
01 - Basic Chat
单轮与多轮对话演示

Usage:
  export HY3_BASE_URL=http://127.0.0.1:8000/v1
  export HY3_API_KEY=EMPTY
  export HY3_MODEL=hy3
  python basic_chat.py

Or use .env file (cp ../../../.env.example ../../../.env)
"""

from openai import OpenAI
import os

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ========== 单轮对话 ==========
print("=" * 50)
print("单轮对话")
print("=" * 50)

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "用一句话解释什么是量子计算。"},
    ],
    temperature=0.9,
    top_p=1.0,
)

print(f"Response:\n{response.choices[0].message.content}\n")
print(f"Usage: {response.usage}\n")

# ========== 多轮对话 ==========
print("=" * 50)
print("多轮对话")
print("=" * 50)

messages = [
    {"role": "user", "content": "推荐几本科幻小说。"},
]

# 第一轮
response = client.chat.completions.create(
    model=MODEL, messages=messages, temperature=0.9,
)
assistant_reply = response.choices[0].message.content
print(f"Assistant (第一轮): {assistant_reply}\n")
messages.append({"role": "assistant", "content": assistant_reply})

# 第二轮：追问
messages.append({"role": "user", "content": "我最喜欢《三体》，能再推荐类似的作品吗？"})
response = client.chat.completions.create(
    model=MODEL, messages=messages, temperature=0.9,
)
print(f"Assistant (第二轮): {response.choices[0].message.content}")
