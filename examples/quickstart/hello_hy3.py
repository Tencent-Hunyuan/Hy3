"""Hello Hy3 — 5-minute quickstart.

Usage::

    export HY3_BASE_URL=http://127.0.0.1:8000/v1
    export HY3_API_KEY=EMPTY
    python hello_hy3.py
"""

import os
from openai import OpenAI

BASE_URL = os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.environ.get("HY3_API_KEY", "EMPTY")
MODEL = os.environ.get("HY3_MODEL", "tencent/Hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# 1. Basic chat
print("=" * 60)
print("1. Basic Chat")
print("=" * 60)
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Hello! What can you do?"}],
    max_tokens=200,
)
print(resp.choices[0].message.content)

# 2. Code generation
print()
print("=" * 60)
print("2. Code Generation")
print("=" * 60)
resp = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "You are a Python expert."},
        {"role": "user", "content": "Write a function that checks if a string is a palindrome."},
    ],
    temperature=0.3,
    max_tokens=500,
)
print(resp.choices[0].message.content)

# 3. Streaming
print()
print("=" * 60)
print("3. Streaming")
print("=" * 60)
stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Count from 1 to 5."}],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
