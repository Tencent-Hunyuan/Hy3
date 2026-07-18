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
"""Hy3 Example 03: Non-streaming vs streaming latency comparison.

Measures:
  - Non-streaming: total latency
  - Streaming: Time To First Token (TTFT) and total latency
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import chat_completion, collect_stream, get_config, make_client  # noqa: E402


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    messages = [
        {
            "role": "user",
            "content": (
                "请用中文简要介绍混合专家模型（MoE）的工作原理，"
                "并举一个生活中的类比，回答约 150 字。"
            ),
        },
    ]

    # ---------- Non-streaming ----------
    print("=== Non-streaming call ===")
    t0 = time.perf_counter()
    response = chat_completion(client, messages, reasoning="no_think", stream=False)
    nonstream_total = time.perf_counter() - t0
    nonstream_text = response.choices[0].message.content
    print(f"Response content:\n{nonstream_text}")
    print(f"\nNon-streaming total latency: {nonstream_total:.3f} s\n")

    # ---------- Streaming ----------
    print("=== Streaming call ===")
    stream = chat_completion(client, messages, reasoning="no_think", stream=True)
    stream_text, ttft, stream_total = collect_stream(stream)
    print(f"Response content:\n{stream_text}")
    ttft_str = f"{ttft:.3f} s" if ttft is not None else "N/A"
    print(f"\nStreaming TTFT (Time To First Token): {ttft_str}")
    print(f"Streaming total latency: {stream_total:.3f} s\n")

    # ---------- Comparison summary ----------
    print("=== Comparison summary ===")
    print(f"Non-streaming total latency:           {nonstream_total:.3f} s")
    print(f"Streaming  TTFT:                       {ttft_str}")
    print(f"Streaming  total latency:              {stream_total:.3f} s")
    if ttft is not None and nonstream_total > 0:
        print(f"TTFT / Non-streaming total latency:    {ttft / nonstream_total:.1%}")
        print(
            "Tip: streaming lets UIs start rendering earlier even when total "
            "generation time is similar."
        )


if __name__ == "__main__":
    main()
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
> Verified live on **Tencent Cloud TokenHub** (`https://tokenhub.tencentmaas.com/v1`, `model=hy3`) on **2026-07-18**. Output is model-generated and may vary; secrets redacted.

```text
=== Comparison summary (TokenHub live) ===
Non-streaming total latency:  1.437 s
Streaming TTFT:               0.001 s
Streaming total latency:      0.592 s

Non-stream text preview:
MoE（混合专家模型）是一种将任务动态分配给多个专用子模型（专家）并由门控网络按需激活部分专家以提升效率与性能的神经网络架构。
```
