"""
02_streaming.py — Hy3 Streaming Request Example
================================================
Demo: Process streaming response chunk by chunk + Full content concatenation

Run:
    python 02_streaming.py

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


# ══════════════════════════════════════════════════════
# Example 1: Basic streaming request
# ══════════════════════════════════════════════════════
def basic_streaming():
    """Receive streaming response chunk by chunk"""
    print("=" * 60)
    print("Example 1: Basic Streaming")
    print("=" * 60)

    print("\n[User]: Describe the history of AI in three sentences.")
    print("[Assistant]: ", end="", flush=True)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Describe the history of AI in three sentences."}
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        stream=True,
    )

    # Process each chunk
    full_content = ""
    chunk_count = 0

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            print(delta.content, end="", flush=True)
            full_content += delta.content
            chunk_count += 1

    print(f"\n\n--- Streaming Stats ---")
    print(f"Total chunks received: {chunk_count}")
    print(f"Total characters: {len(full_content)}")
    return full_content


# ══════════════════════════════════════════════════════
# Example 2: Streaming + TTFT measurement
# ══════════════════════════════════════════════════════
def streaming_with_metrics():
    """Streaming request with key performance metrics measurement"""
    print("\n" + "=" * 60)
    print("Example 2: Streaming + Performance Metrics")
    print("=" * 60)

    prompt = "Explain the core principles of the Transformer architecture in detail."
    print(f"\n[User]: {prompt}")
    print("[Assistant]: ", end="", flush=True)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=1024,
        stream=True,
    )

    # Performance metrics collection
    first_token_time = None
    start_time = time.time()
    full_content = ""
    token_count = 0

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            # Record time-to-first-token
            if first_token_time is None:
                first_token_time = time.time()
            print(delta.content, end="", flush=True)
            full_content += delta.content
            token_count += 1

    end_time = time.time()

    # Output performance report
    ttft = (first_token_time - start_time) if first_token_time else 0
    total = end_time - start_time

    print(f"\n\n--- Performance Report ---")
    print(f"Time to First Token (TTFT): {ttft:.3f}s")
    print(f"Total Duration:             {total:.3f}s")
    print(f"Generation Time:            {total - ttft:.3f}s")
    print(f"Chunks Received:            {token_count}")
    if token_count > 0 and total > 0:
        print(f"Approx Throughput:          {token_count / total:.1f} chunks/s")

    return {
        "ttft": ttft,
        "total_duration": total,
        "chunk_count": token_count,
    }


# ══════════════════════════════════════════════════════
# Example 3: Streaming + real-time progress display
# ══════════════════════════════════════════════════════
def streaming_with_progress():
    """Streaming request with real-time generation progress display"""
    print("\n" + "=" * 60)
    print("Example 3: Streaming + Real-time Progress")
    print("=" * 60)

    prompt = "Write a seven-character quatrain about code."
    print(f"\n[User]: {prompt}")
    print("[Assistant]: ", end="", flush=True)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=256,
        stream=True,
    )

    full_content = ""
    for chunk in stream:
        delta = chunk.choices[0].delta
        finish = chunk.choices[0].finish_reason
        if delta.content:
            print(delta.content, end="", flush=True)
            full_content += delta.content
        if finish:
            print(f"\n  [finish_reason: {finish}]")

    print(f"\n--- Full Content ---")
    print(full_content)
    return full_content


# ── Main entry ───────────────────────────────────────────
if __name__ == "__main__":
    print("Hy3 Streaming Request Example")
    print(f"API: {BASE_URL} | Model: {MODEL}\n")

    basic_streaming()
    streaming_with_metrics()
    streaming_with_progress()

    print("\n" + "=" * 60)
    print("All streaming examples completed!")
    print("=" * 60)
