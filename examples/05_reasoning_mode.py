"""Hy3 example 05: compare reasoning modes."""

import os
import time
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=180.0)

PROMPT = "一个水池有进水管和出水管。进水管 6 小时注满，出水管 9 小时放空。两管同时开，多久注满？请给出答案。"

for mode in ["no_think", "high"]:
    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.2,
        max_tokens=900,
        extra_body={"chat_template_kwargs": {"reasoning_effort": mode}},
    )
    elapsed = time.perf_counter() - t0
    message = response.choices[0].message
    reasoning_content = getattr(message, "reasoning_content", None)

    print(f"\n=== reasoning_effort={mode} ===")
    print(f"elapsed_s: {elapsed:.3f}")
    print("answer:")
    print(message.content)

    if reasoning_content:
        print("reasoning_content_detected: yes")
        print("reasoning_preview:", reasoning_content[:300].replace("\n", " "), "...")
    else:
        print("reasoning_content_detected: no")
    print("usage:", response.usage)
