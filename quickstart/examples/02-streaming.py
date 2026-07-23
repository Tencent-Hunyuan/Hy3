"""
Example 2: Streaming — token-by-token response streaming with Hy3.

Usage:
    python 02-streaming.py

Prerequisites:
    - Hy3 server running at http://127.0.0.1:8000 (vLLM or SGLang)
    - pip install openai
"""

import time
from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ──────────────────────────────────────────────────────────────────────
# 1. Basic Streaming
# ──────────────────────────────────────────────────────────────────────
def basic_streaming():
    print("=" * 60)
    print("1. BASIC STREAMING")
    print("=" * 60)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Write a haiku about programming."},
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=256,
        stream=True,
    )

    print("\nStreaming output:\n")
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # Print content token by token
        if delta.content:
            print(delta.content, end="", flush=True)

        # Finish reason
        if chunk.choices[0].finish_reason:
            print(f"\n\n[Finished: {chunk.choices[0].finish_reason}]")

        # Usage stats (final chunk only)
        if hasattr(chunk, "usage") and chunk.usage:
            print(f"[Prompt: {chunk.usage.prompt_tokens} | "
                  f"Completion: {chunk.usage.completion_tokens} | "
                  f"Total: {chunk.usage.total_tokens}]")


# ──────────────────────────────────────────────────────────────────────
# 2. Streaming with Reasoning Content
# ──────────────────────────────────────────────────────────────────────
def streaming_with_reasoning():
    print("\n" + "=" * 60)
    print("2. STREAMING WITH REASONING MODE")
    print("=" * 60)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "A bat and a ball cost $1.10 in total. "
                                        "The bat costs $1.00 more than the ball. "
                                        "How much does the ball cost?"},
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        stream=True,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
    )

    thinking_parts = []
    answer_parts = []

    print("\nThinking (dim):")
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # Reasoning content (thinking process)
        if getattr(delta, "reasoning_content", None):
            thinking_parts.append(delta.reasoning_content)
            print(f"\x1b[90m{delta.reasoning_content}\x1b[0m", end="", flush=True)

        # Final answer content
        if delta.content:
            answer_parts.append(delta.content)
            print(delta.content, end="", flush=True)

        if chunk.choices[0].finish_reason:
            print(f"\n\n[Finish reason: {chunk.choices[0].finish_reason}]")

    if thinking_parts:
        print(f"\n[Thinking: {len(''.join(thinking_parts))} chars]")
    if answer_parts:
        print(f"[Answer: {len(''.join(answer_parts))} chars]")


# ──────────────────────────────────────────────────────────────────────
# 3. Stream and Collect Full Response
# ──────────────────────────────────────────────────────────────────────
def stream_and_collect(messages, **kwargs):
    """Stream the response in real-time and return the full text + metadata."""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=True,
        **kwargs,
    )

    content_parts = []
    reasoning_parts = []
    finish_reason = None
    usage = None
    first_token_time = None
    start_time = time.time()

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # Track time to first token
        if first_token_time is None and (
            delta.content or getattr(delta, "reasoning_content", None)
        ):
            first_token_time = time.time()

        if getattr(delta, "reasoning_content", None):
            reasoning_parts.append(delta.reasoning_content)

        if delta.content:
            content_parts.append(delta.content)
            print(delta.content, end="", flush=True)

        if chunk.choices[0].finish_reason:
            finish_reason = chunk.choices[0].finish_reason

        if hasattr(chunk, "usage") and chunk.usage:
            usage = chunk.usage

    elapsed = time.time() - start_time
    ttft = (first_token_time - start_time) if first_token_time else None

    return {
        "content": "".join(content_parts),
        "reasoning": "".join(reasoning_parts),
        "finish_reason": finish_reason,
        "usage": usage,
        "elapsed_s": elapsed,
        "ttft_s": ttft,
    }


def streaming_with_timing():
    print("\n" + "=" * 60)
    print("3. STREAMING WITH TIMING")
    print("=" * 60)

    result = stream_and_collect(
        messages=[{"role": "user", "content": "Explain how SSL/TLS works in 3 paragraphs."}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
    )

    print(f"\n\n--- Timing ---")
    print(f"Time to first token (TTFT): {result['ttft_s']:.2f}s" if result['ttft_s'] else "TTFT: N/A")
    print(f"Total elapsed: {result['elapsed_s']:.2f}s")
    print(f"Finish reason: {result['finish_reason']}")
    if result["usage"]:
        print(f"Tokens: prompt={result['usage'].prompt_tokens}, "
              f"completion={result['usage'].completion_tokens}, "
              f"total={result['usage'].total_tokens}")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    basic_streaming()
    streaming_with_reasoning()
    streaming_with_timing()
