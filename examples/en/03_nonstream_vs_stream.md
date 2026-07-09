# 03 Non-streaming vs Streaming Latency Comparison Example

## Introduction

This example calls Hy3 with the **same prompt** in both non-streaming and streaming modes, using `time.perf_counter()` for high-precision timing, and compares two key latency metrics:

- **Non-streaming**: waits for the model to finish generating the full result before returning; mainly measures **total latency**.
- **Streaming**: the model generates and pushes chunks as it goes; two metrics are measured:
  - **TTFT (Time To First Token)**: the time from sending the request to receiving the first non-empty `delta.content`.
  - **Total latency**: the time from sending the request to the end of stream iteration (receiving the last chunk).

The comparison shows intuitively that the **TTFT of a streaming call is far smaller than the total latency of a non-streaming call**, so streaming is better suited for interactive scenarios; non-streaming is simpler and more direct for **batch processing / post-processing** scenarios.

---

## Complete Request

> Before running, deploy the Hy3 service via vLLM / SGLang (listens on `127.0.0.1:8000` by default).
> Connection info can be overridden via the environment variables `HY3_BASE_URL` and `HY3_API_KEY`.

```python
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
```

---

## Complete Response Parsing

### 1. Non-streaming response (`stream=False`)

A non-streaming call **blocks** until the model has generated the entire answer, then returns one complete `ChatCompletion` object at once:

```python
response = client.chat.completions.create(**common_kwargs, stream=False)
# response.choices[0].message.content is the full text
```

- **Timing**: record `t0 = time.perf_counter()` before the call and `t1` after it returns; `non-streaming total latency = t1 - t0`. This equals the network round-trip plus the time for the model to generate all tokens.
- The text can be read directly from `response.choices[0].message.content` in one shot — no concatenation needed.
- `response.usage` usually has a value, so token usage is directly available.

### 2. Streaming response (`stream=True`)

A streaming call immediately returns an iterator; the model pushes `ChatCompletionChunk`s as it generates:

```python
stream = client.chat.completions.create(**common_kwargs, stream=True)
```

- **TTFT measurement**:
  - Record `t0 = time.perf_counter()` before issuing the call.
  - Iterate over chunks; when the first **non-empty** `delta.content` is encountered, `TTFT = time.perf_counter() - t0`, and stop updating TTFT (use `if ttft is None` so it is recorded only once).
  - Be sure to skip chunks whose `delta.content` is `None` or `""` (e.g. the first frame that only carries `role`).
- **Total latency**: record `t1` after the stream iteration ends; `streaming total latency = t1 - t0`, which includes TTFT plus the generation and transmission time of all subsequent tokens.
- The text must be assembled yourself with `"".join(parts)`.
- By default `chunk.usage` is `None`; pass `stream_options={"include_usage": True}` if you need usage.

### 3. Relationship between the two

- When the generated content is the same, **streaming total latency ≈ non-streaming total latency** (the generation workload is comparable; the difference mainly comes from chunked transmission and the network).
- The key difference is **time to first character**: under non-streaming the user must wait for the full `total latency` before seeing anything; under streaming the user sees the first character after `TTFT` (usually much smaller than total latency), which feels smoother.
- The ratio `TTFT / non-streaming total latency` reflects "the proportion of time the user must wait" and is an important indicator of interactive experience.

### 4. When to use which mode

| Mode | Pros | Suitable scenarios |
|:---|:---|:---|
| Non-streaming | Get the full result at once; simple code; `usage` directly available | Batch inference, post-processing, structured extraction, downstream processing that needs the full text |
| Streaming | Low TTFT; can display while generating; feels smooth | Chat assistants, interactive Q&A, real-time writing, terminal typewriter effects |

> Prefer `time.perf_counter()` over `time.time()` for timing: the former is a high-precision monotonic clock suited to measuring short intervals and is not affected by system clock adjustments.

---

## Sample Output

> The following is **sample output** (representative data, not a real run result). Actual values depend on hardware, load, generation length, and other factors.

```
=== Non-streaming call ===
Response content:
混合专家模型（MoE）通过门控网络为每个 token 动态选择少量"专家"子网络进行计算，从而在扩大总参数量的同时保持较低的激活参数量与推理成本。生活中可以类比为医院分诊：患者（token）进入后，分诊台（门控）根据症状把它分配给最合适的几位专科医生（专家）诊治，而不是让所有医生都同时参与。

Non-streaming total latency: 3.842 s

=== Streaming call ===
Response content:
混合专家模型（MoE）通过门控网络为每个 token 动态选择少量"专家"子网络进行计算，从而在扩大总参数量的同时保持较低的激活参数量与推理成本。生活中可以类比为医院分诊：患者（token）进入后，分诊台（门控）根据症状把它分配给最合适的几位专科医生（专家）诊治，而不是让所有医生都同时参与。

Streaming TTFT (Time To First Token): 0.237 s
Streaming total latency: 3.798 s

=== Comparison summary ===
Non-streaming total latency:           3.842 s
Streaming  TTFT:                       0.237 s
Streaming  total latency:              3.798 s
TTFT / Non-streaming total latency:    6.2%
```

As you can see: the **total latencies of the two modes are close** (the generation length is the same), but the streaming **TTFT (0.237 s) is far smaller than the non-streaming total latency (3.842 s)** — the user sees the first character after about 0.24 seconds, whereas with non-streaming they must wait nearly 3.8 seconds before seeing any output. This is exactly the core value of streaming calls in interactive scenarios.
