"""Hy3 example 03: compare non-streaming vs streaming latency."""

import os
import time
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=180.0)

messages = [{"role": "user", "content": "请写一段约 300 字的说明，解释为什么 API 文档需要 quickstart 和 examples。"}]
common_args = dict(
    model=MODEL,
    messages=messages,
    temperature=0.7,
    top_p=1.0,
    max_tokens=700,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

t0 = time.perf_counter()
non_stream_resp = client.chat.completions.create(**common_args)
non_stream_total = time.perf_counter() - t0
non_stream_text = non_stream_resp.choices[0].message.content or ""

t0 = time.perf_counter()
first_token_time = None
stream_text_parts = []
stream = client.chat.completions.create(**common_args, stream=True)

for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    content = getattr(delta, "content", None)
    if content:
        if first_token_time is None:
            first_token_time = time.perf_counter() - t0
        stream_text_parts.append(content)
stream_total = time.perf_counter() - t0

print("=== latency comparison ===")
print(f"non_stream_total_s: {non_stream_total:.3f}")
print(f"stream_first_token_s: {first_token_time:.3f}" if first_token_time else "stream_first_token_s: n/a")
print(f"stream_total_s: {stream_total:.3f}")
print(f"non_stream_chars: {len(non_stream_text)}")
print(f"stream_chars: {len(''.join(stream_text_parts))}")
