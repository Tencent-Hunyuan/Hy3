"""
03_latency_compare.py — Hy3 Streaming vs Non-streaming Latency Comparison
==========================================================================
Demo: Compare TTFT and total duration between streaming and non-streaming modes

Run:
    python 03_latency_compare.py

Environment Variables:
    HY3_BASE_URL  - API endpoint (default: http://127.0.0.1:8000/v1)
    HY3_API_KEY   - API key (default: EMPTY)
    HY3_MODEL     - Model name (default: hy3)
"""

import os
import time
from openai import OpenAI

# ── Configuration ────────────────────────────────────────
BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def non_streaming_request(prompt: str, max_tokens: int = 512) -> dict:
    """Non-streaming request: wait for complete response and return at once"""
    start = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=max_tokens,
        stream=False,
    )
    end = time.time()

    return {
        "mode": "non-streaming",
        "content": response.choices[0].message.content,
        "total_duration": end - start,
        "ttft": end - start,  # In non-streaming mode, TTFT ≈ total duration
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }


def streaming_request(prompt: str, max_tokens: int = 512) -> dict:
    """Streaming request: receive chunk by chunk, can measure TTFT"""
    start = time.time()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=max_tokens,
        stream=True,
    )

    first_token_time = None
    full_content = ""
    chunk_count = 0

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            # Record time-to-first-token
            if first_token_time is None:
                first_token_time = time.time()
            full_content += delta.content
            chunk_count += 1

    end = time.time()
    ttft = (first_token_time - start) if first_token_time else 0

    return {
        "mode": "streaming",
        "content": full_content,
        "total_duration": end - start,
        "ttft": ttft,
        "chunks": chunk_count,
    }


# ══════════════════════════════════════════════════════
# Comparison test
# ══════════════════════════════════════════════════════
def run_comparison():
    """Run streaming and non-streaming requests for the same prompt, compare latency"""

    # Three test prompts of different lengths
    prompts = [
        ("Short", "What's the difference between list and tuple in Python?", 128),
        ("Medium", "Explain the Attention Mechanism and give an intuitive example.", 512),
        ("Long", "Write an ~800-word tech blog on 'Main Strategies for LLM Inference Optimization'.", 1024),
    ]

    results = []

    for label, prompt, max_tokens in prompts:
        print(f"\n{'=' * 60}")
        print(f"Test Scenario: {label} (max_tokens={max_tokens})")
        print(f"Prompt: {prompt[:50]}...")
        print(f"{'=' * 60}")

        # Non-streaming request
        print("\n>>> Running non-streaming request...")
        non_stream = non_streaming_request(prompt, max_tokens)
        print(f"    Total Duration: {non_stream['total_duration']:.3f}s")
        print(f"    Response Length: {len(non_stream['content'])} chars")
        print(f"    Tokens: {non_stream['completion_tokens']}")

        # Streaming request
        print("\n>>> Running streaming request...")
        stream = streaming_request(prompt, max_tokens)
        print(f"    TTFT:   {stream['ttft']:.3f}s")
        print(f"    Total Duration: {stream['total_duration']:.3f}s")
        print(f"    Response Length: {len(stream['content'])} chars")
        print(f"    Chunks: {stream['chunks']}")

        # Comparison
        print(f"\n--- Comparison ---")
        ttft_improvement = (
            (1 - stream["ttft"] / non_stream["total_duration"]) * 100
            if non_stream["total_duration"] > 0
            else 0
        )
        print(f"    Streaming TTFT vs Non-streaming Total: "
              f"Improvement {ttft_improvement:.1f}%")
        print(f"    Total Duration Diff: "
              f"{abs(non_stream['total_duration'] - stream['total_duration']):.3f}s")

        results.append({
            "label": label,
            "non_streaming": non_stream,
            "streaming": stream,
            "ttft_improvement_pct": ttft_improvement,
        })

    # Summary table
    print(f"\n\n{'=' * 60}")
    print("Summary Report")
    print(f"{'=' * 60}")
    print(f"{'Scenario':<12} {'Non-stream(s)':<16} {'Stream TTFT(s)':<18} {'Stream Total(s)':<18} {'TTFT Improve':<14}")
    print("-" * 78)
    for r in results:
        print(
            f"{r['label']:<12} "
            f"{r['non_streaming']['total_duration']:<16.3f} "
            f"{r['streaming']['ttft']:<18.3f} "
            f"{r['streaming']['total_duration']:<18.3f} "
            f"{r['ttft_improvement_pct']:<13.1f}%"
        )

    # Conclusions
    print(f"\n--- Conclusions ---")
    print("1. Streaming TTFT is significantly lower than non-streaming total duration.")
    print("2. Total durations are similar (streaming slightly higher due to network overhead).")
    print("3. For interactive scenarios, streaming provides better UX as users don't wait for the full response.")
    print("4. For batch processing, non-streaming is simpler with cleaner code.")

    return results


# ── Main entry ───────────────────────────────────────────
if __name__ == "__main__":
    print("Hy3 Streaming vs Non-streaming Latency Comparison")
    print(f"API: {BASE_URL} | Model: {MODEL}\n")

    run_comparison()
