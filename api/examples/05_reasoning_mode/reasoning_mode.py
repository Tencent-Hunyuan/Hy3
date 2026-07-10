"""
05 - Reasoning Mode
演示思考过程开启与关闭的对比

Usage:
  export HY3_BASE_URL=http://127.0.0.1:8000/v1
  export HY3_API_KEY=EMPTY
  export HY3_MODEL=hy3
  python reasoning_mode.py
"""

from openai import OpenAI
import os

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

messages = [
    {"role": "user",
     "content": "一个水池有一个进水管和一个出水管。单开进水管 3 小时注满，单开出水管 5 小时排空。"
                "如果同时打开，多久能注满？"}
]

# ===== no_think: 关闭思考，直接回复 =====
print("=" * 50)
print("reasoning_effort = no_think（关闭思考）")
print("=" * 50)

response_no_think = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.9,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print(f"回复: {response_no_think.choices[0].message.content}\n")

# ===== low: 轻度思考 =====
print("=" * 50)
print("reasoning_effort = low（轻度思考）")
print("=" * 50)

response_low = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.9,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "low"}},
)
msg = response_low.choices[0].message
if hasattr(msg, "reasoning_content") and msg.reasoning_content:
    print(f"思考过程: {msg.reasoning_content}")
print(f"回复: {msg.content}\n")

# ===== high: 深度思考 =====
print("=" * 50)
print("reasoning_effort = high（深度思考）")
print("=" * 50)

response_high = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.9,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
msg = response_high.choices[0].message
if hasattr(msg, "reasoning_content") and msg.reasoning_content:
    print(f"思考过程: {msg.reasoning_content}")
print(f"回复: {msg.content}")
