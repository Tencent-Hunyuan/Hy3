"""
Hy3 Non-streaming vs Streaming Latency Comparison Example (examples/03_nonstream_vs_stream.py)

Calls Hy3 with the same prompt in both non-streaming and streaming modes,
using time.perf_counter() to measure:
    - Non-streaming: total latency (waiting for the full generation to return)
    - Streaming: Time To First Token (TTFT, when the first non-empty delta.content arrives) and total latency

Before running, deploy the Hy3 service via vLLM / SGLang (listens on 127.0.0.1:8000 by default).
Connection info can be overridden via environment variables:
    HY3_BASE_URL  service address (default http://127.0.0.1:8000/v1)
    HY3_API_KEY   API key (any value works for local deployment, default EMPTY)
"""

import os
import time

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

# Fixed comparison prompt
messages = [
    {
        "role": "user",
        "content": (
            "请用中文简要介绍混合专家模型（MoE）的工作原理，"
            "并举一个生活中的类比，回答约 150 字。"
        ),
    },
]

common_kwargs = dict(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

# ---------- Non-streaming ----------
print("=== Non-streaming call ===")
t0 = time.perf_counter()
response = client.chat.completions.create(**common_kwargs, stream=False)
t1 = time.perf_counter()
nonstream_total = t1 - t0
nonstream_text = response.choices[0].message.content
print(f"Response content:\n{nonstream_text}")
print(f"\nNon-streaming total latency: {nonstream_total:.3f} s\n")

# ---------- Streaming ----------
print("=== Streaming call ===")
t0 = time.perf_counter()
stream = client.chat.completions.create(**common_kwargs, stream=True)
ttft = None
parts = []
for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    content = delta.content
    if content:  # first non-empty token
        if ttft is None:
            ttft = time.perf_counter() - t0
        parts.append(content)
t1 = time.perf_counter()
stream_total = t1 - t0
stream_text = "".join(parts)
print(f"Response content:\n{stream_text}")
print(f"\nStreaming TTFT (Time To First Token): {ttft:.3f} s")
print(f"Streaming total latency: {stream_total:.3f} s\n")

# ---------- Comparison summary ----------
print("=== Comparison summary ===")
print(f"Non-streaming total latency:           {nonstream_total:.3f} s")
print(f"Streaming  TTFT:                       {ttft:.3f} s")
print(f"Streaming  total latency:              {stream_total:.3f} s")
if ttft is not None:
    print(f"TTFT / Non-streaming total latency:    {ttft / nonstream_total:.1%}")
