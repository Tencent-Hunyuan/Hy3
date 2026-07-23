# Example 3: Non-Streaming vs Streaming — Latency Comparison

Compare time-to-first-token (TTFT) and total elapsed time between non-streaming and streaming modes.

## What You'll Learn

- Measure TTFT (time to first token) for both modes
- Measure total response time
- Understand the UX tradeoffs
- Choose the right mode for your use case

---

## Comparison Setup

Same prompt, same parameters — only `stream` flag changes.

```python
import time
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

PROMPT = "Explain the differences between TCP and UDP in detail."
```

### Non-Streaming

```python
def non_streaming_call():
    start = time.time()

    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        stream=False,
    )

    elapsed = time.time() - start
    content = response.choices[0].message.content

    return {
        "mode": "non-streaming",
        "ttft_s": elapsed,  # No TTFT — entire response arrives at once
        "total_s": elapsed,
        "content_length": len(content),
        "tokens": response.usage.completion_tokens,
    }
```

### Streaming

```python
def streaming_call():
    start = time.time()
    first_token_time = None

    stream = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        stream=True,
    )

    content_parts = []
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        if first_token_time is None and delta.content:
            first_token_time = time.time()

        if delta.content:
            content_parts.append(delta.content)

    elapsed = time.time() - start
    ttft = (first_token_time - start) if first_token_time else None

    return {
        "mode": "streaming",
        "ttft_s": ttft,
        "total_s": elapsed,
        "content_length": len("".join(content_parts)),
    }
```

### Results Comparison

```python
def compare():
    results = []
    for func in [non_streaming_call, streaming_call]:
        result = func()
        results.append(result)
        print(f"Mode: {result['mode']}")
        print(f"  TTFT:      {result['ttft_s']:.2f}s")
        print(f"  Total:     {result['total_s']:.2f}s")
        print(f"  Length:    {result['content_length']} chars")
        print()
```

### Expected Output

```
Mode: non-streaming
  TTFT:      4.83s   ← User sees NOTHING for 4.83s
  Total:     4.83s
  Length:    1024 chars

Mode: streaming
  TTFT:      0.31s   ← User sees first token in 0.31s!
  Total:     5.12s   ← Slightly more overhead overall
  Length:    1024 chars
```

---

## Analysis

| Metric | Non-Streaming | Streaming | Winner |
|:---|:---|:---|:---|
| **Time to first visible output** | = total time (~4.8s) | ~0.3s | ✅ Streaming |
| **Total response time** | ~4.8s | ~5.1s | ✅ Non-streaming (slightly) |
| **Perceived responsiveness** | Poor (long blank wait) | Excellent (instant feedback) | ✅ Streaming |
| **Implementation complexity** | Simple | Moderate | ✅ Non-streaming |
| **Best for** | Backend/batch processing | User-facing chat UIs | — |

### When to Use Each Mode

**Use Non-Streaming for:**
- Backend processing (no user waiting)
- Batch jobs where you need the full response to proceed
- Tool calling — you need the complete `tool_calls` before executing
- Simple scripts and automation

**Use Streaming for:**
- Chat interfaces — users see responses as they're generated
- Long-form content generation — avoids the "spinning wheel" UX
- Real-time applications (voice assistants, live captioning)
- When reasoning mode is on — users can see the thinking process

---

## Multi-Run Benchmark

For reliable numbers, run multiple iterations:

```python
import statistics

def benchmark(func, runs=5):
    times = []
    for _ in range(runs):
        result = func()
        times.append(result["total_s"])
    return {
        "min": min(times),
        "max": max(times),
        "mean": statistics.mean(times),
        "stdev": statistics.stdev(times) if len(times) > 1 else 0,
    }

ns_stats = benchmark(non_streaming_call, runs=5)
s_stats = benchmark(streaming_call, runs=5)

print("Non-streaming (5 runs):")
print(f"  Mean: {ns_stats['mean']:.2f}s ± {ns_stats['stdev']:.2f}s")
print(f"  Range: {ns_stats['min']:.2f}s – {ns_stats['max']:.2f}s")

print("\nStreaming (5 runs):")
print(f"  Mean: {s_stats['mean']:.2f}s ± {s_stats['stdev']:.2f}s")
print(f"  Range: {s_stats['min']:.2f}s – {s_stats['max']:.2f}s")
```

### Sample Output (5 runs)

```
Non-streaming (5 runs):
  Mean: 4.91s ± 0.34s
  Range: 4.53s – 5.41s

Streaming (5 runs):
  Mean: 5.18s ± 0.41s
  Range: 4.72s – 5.83s
```

---

## Key Takeaways

1. **Streaming delivers ~10-20× faster perceived first response** (TTFT of ~0.3s vs ~5s total).
2. **Streaming has ~5-10% overhead** in total time due to SSE framing.
3. **User experience trumps raw speed** — always use streaming for interactive UIs.
4. **Network conditions matter** — streaming performs better on high-latency connections because the user sees output immediately.
5. **MTP speculative decoding** (enabled by default in the vLLM recipe) improves both modes significantly.

---

## Run the Script

```bash
pip install openai
python 03-latency-comparison.py
```
