"""
03 - Non-streaming vs Streaming
比较非流式与流式请求的首 token 时延和总耗时

Usage:
  export HY3_BASE_URL=http://127.0.0.1:8000/v1
  export HY3_API_KEY=EMPTY
  export HY3_MODEL=hy3
  python nonstreaming_vs_streaming.py
"""

import time
from openai import OpenAI
import os

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

messages = [
    {"role": "user",
     "content": "请详细解释机器学习中的 Transformer 架构，包括自注意力机制的原理。"},
]

# ===== Non-streaming =====
print("=" * 50)
print("Non-streaming")
print("=" * 50)

start = time.time()
response = client.chat.completions.create(
    model=MODEL, messages=messages, temperature=0.9,
)
non_streaming_total = time.time() - start
non_streaming_content = response.choices[0].message.content

print(f"总耗时: {non_streaming_total:.2f}s")
print(f"输出长度: {len(non_streaming_content)} 字符")
print(f"Usage: {response.usage}")

# ===== Streaming =====
print("\n" + "=" * 50)
print("Streaming")
print("=" * 50)

start = time.time()
first_token_time = None
stream = client.chat.completions.create(
    model=MODEL, messages=messages,
    stream=True, temperature=0.9,
)

streaming_content = ""
for chunk in stream:
    if first_token_time is None and chunk.choices and chunk.choices[0].delta.content:
        first_token_time = time.time() - start
    if chunk.choices and chunk.choices[0].delta.content:
        streaming_content += chunk.choices[0].delta.content

streaming_total = time.time() - start

print(f"首 token 时延: {first_token_time:.2f}s")
print(f"总耗时: {streaming_total:.2f}s")
print(f"输出长度: {len(streaming_content)} 字符")

# ===== 对比总结 =====
print("\n" + "=" * 50)
print("对比总结")
print("=" * 50)
print(f"Non-streaming 总耗时: {non_streaming_total:.2f}s")
print(f"Streaming 首 token 时延: {first_token_time:.2f}s")
print(f"Streaming 总耗时: {streaming_total:.2f}s")
print(f"输出一致: {non_streaming_content == streaming_content}")
