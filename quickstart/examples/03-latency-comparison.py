"""
Example 3: Non-Streaming vs Streaming — Latency Comparison.

Compares time-to-first-token (TTFT) and total elapsed time between
non-streaming and streaming modes. Use this to decide which mode
fits your use case.

Usage:
    python 03-latency-comparison.py

Prerequisites:
    - Hy3 server running at http://127.0.0.1:8000 (vLLM or SGLang)
    - pip install openai
"""

import time
import statistics
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"
BENCHMARK_RUNS = 3  # Number of runs per mode for averaging

PROMPT = (
    "Explain the key differences between TCP and UDP protocols. "
    "Cover reliability, ordering, congestion control, use cases, and "
    "the tradeoffs involved in choosing one over the other."
)

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ──────────────────────────────────────────────────────────────────────
# 1. Non-Streaming Call
# ──────────────────────────────────────────────────────────────────────
def non_streaming_call():
    """Make a non-streaming request and measure timing."""
    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        stream=False,
    )

    elapsed = time.perf_counter() - start
    content = response.choices[0].message.content

    return {
        "mode": "non-streaming",
        "ttft_s": elapsed,  # Same as total — user sees everything at once
        "total_s": elapsed,
        "content_chars": len(content),
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }


# ──────────────────────────────────────────────────────────────────────
# 2. Streaming Call
# ──────────────────────────────────────────────────────────────────────
def streaming_call():
    """Make a streaming request and measure TTFT + total time."""
    start = time.perf_counter()
    first_token_time = None

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        stream=True,
    )

    content_parts = []
    usage = None

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # Record time to first content token
        if first_token_time is None and delta.content:
            first_token_time = time.perf_counter()

        if delta.content:
            content_parts.append(delta.content)

        if hasattr(chunk, "usage") and chunk.usage:
            usage = chunk.usage

    elapsed = time.perf_counter() - start
    ttft = (first_token_time - start) if first_token_time else None

    return {
        "mode": "streaming",
        "ttft_s": ttft,
        "total_s": elapsed,
        "content_chars": len("".join(content_parts)),
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
    }


# ──────────────────────────────────────────────────────────────────────
# 3. Benchmark Runner
# ──────────────────────────────────────────────────────────────────────
def benchmark(func, runs=BENCHMARK_RUNS):
    """Run a call function multiple times and return timing statistics."""
    results = []
    for i in range(runs):
        print(f"  Run {i + 1}/{runs}...", end=" ", flush=True)
        result = func()
        results.append(result)
        print(f"→ {result['total_s']:.2f}s total, "
              f"{result.get('ttft_s') or result['total_s']:.2f}s TTFT")

    times = [r["total_s"] for r in results]
    ttfts = [r.get("ttft_s") or r["total_s"] for r in results]

    return {
        "mode": results[0]["mode"],
        "runs": runs,
        "total_mean": statistics.mean(times),
        "total_stdev": statistics.stdev(times) if len(times) > 1 else 0,
        "total_min": min(times),
        "total_max": max(times),
        "ttft_mean": statistics.mean(ttfts),
        "ttft_stdev": statistics.stdev(ttfts) if len(ttfts) > 1 else 0,
        "avg_content_chars": statistics.mean(r["content_chars"] for r in results),
        "avg_completion_tokens": statistics.mean(
            r["completion_tokens"] for r in results if r["completion_tokens"]
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 4. Single-Run Comparison (Detailed)
# ──────────────────────────────────────────────────────────────────────
def detailed_comparison():
    """Run both modes once and show detailed comparison."""
    print("=" * 60)
    print("DETAILED COMPARISON (Single Run)")
    print("=" * 60)

    print("\nRunning non-streaming...", end=" ", flush=True)
    ns = non_streaming_call()
    print(f"done ({ns['total_s']:.2f}s)")

    print("Running streaming...", end=" ", flush=True)
    s = streaming_call()
    print(f"done ({s['total_s']:.2f}s)")

    # ── Results Table ──
    print(f"\n{'Metric':<35} {'Non-Streaming':<20} {'Streaming':<20}")
    print("-" * 75)
    print(f"{'TTFT (time to first token)':<35} {f'{ns['ttft_s']:.2f}s':<20} {f'{s['ttft_s']:.2f}s':<20}")
    print(f"{'Total elapsed':<35} {f'{ns['total_s']:.2f}s':<20} {f'{s['total_s']:.2f}s':<20}")
    print(f"{'Content length (chars)':<35} {ns['content_chars']:<20} {s['content_chars']:<20}")
    print(f"{'Completion tokens':<35} {ns['completion_tokens']:<20} {s['completion_tokens']:<20}")
    print(f"{'Total tokens':<35} {ns['total_tokens']:<20} {s['total_tokens']:<20}")

    # UX analysis
    speedup = ns['ttft_s'] / s['ttft_s'] if s['ttft_s'] and s['ttft_s'] > 0 else 0
    print(f"\n📊 Streaming delivers first visible output {speedup:.0f}× faster "
          f"({ns['ttft_s']:.2f}s → {s['ttft_s']:.2f}s)")

    overhead_pct = ((s['total_s'] - ns['total_s']) / ns['total_s']) * 100
    print(f"📊 Streaming overhead: {overhead_pct:+.1f}% in total response time")


# ──────────────────────────────────────────────────────────────────────
# 5. Multi-Run Benchmark
# ──────────────────────────────────────────────────────────────────────
def multi_run_benchmark():
    """Run multiple iterations for statistically meaningful results."""
    print("\n" + "=" * 60)
    print(f"MULTI-RUN BENCHMARK ({BENCHMARK_RUNS} runs each)")
    print("=" * 60)

    print("\nNon-streaming:")
    ns_stats = benchmark(non_streaming_call)

    print("\nStreaming:")
    s_stats = benchmark(streaming_call)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for stats in [ns_stats, s_stats]:
        print(f"\n{stats['mode'].upper()}:")
        print(f"  Total time:  {stats['total_mean']:.2f}s ± {stats['total_stdev']:.2f}s "
              f"(range: {stats['total_min']:.2f}s – {stats['total_max']:.2f}s)")
        print(f"  TTFT:        {stats['ttft_mean']:.2f}s ± {stats['ttft_stdev']:.2f}s")
        print(f"  Avg chars:   {stats['avg_content_chars']:.0f}")
        print(f"  Avg tokens:  {stats['avg_completion_tokens']:.0f}")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    detailed_comparison()
    multi_run_benchmark()
