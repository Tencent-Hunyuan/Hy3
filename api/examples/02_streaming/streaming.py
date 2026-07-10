"""
02 - Streaming
流式请求与逐 chunk 解析

Usage:
  export HY3_BASE_URL=http://127.0.0.1:8000/v1
  export HY3_API_KEY=EMPTY
  export HY3_MODEL=hy3
  python streaming.py
"""

from openai import OpenAI
import os

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

stream = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "请写一段 200 字左右的短文，主题是人工智能的未来。"},
    ],
    stream=True,
    stream_options={"include_usage": True},
    temperature=0.9,
    top_p=1.0,
)

full_content = ""
for chunk in stream:
    delta = chunk.choices[0].delta if chunk.choices else None

    if delta and delta.content:
        content = delta.content
        full_content += content
        print(content, end="", flush=True)

    if chunk.choices and chunk.choices[0].finish_reason:
        print(f"\n\nFinish reason: {chunk.choices[0].finish_reason}")

    if hasattr(chunk, "usage") and chunk.usage:
        print(f"Usage: {chunk.usage}")

print(f"\n--- 完整输出 ({len(full_content)} 字符) ---")
