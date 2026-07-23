"""
Example 5: Reasoning Mode — compare fast vs. deep thinking on the same prompts.

Usage:
    python 05-reasoning-mode.py

Prerequisites:
    - Hy3 server running at http://127.0.0.1:8000 (vLLM or SGLang)
    - vLLM must be launched with --reasoning-parser hy_v3
      or SGLang with --reasoning-parser hunyuan
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
# 1. Fast Thinking (no_think) — Default Mode
# ──────────────────────────────────────────────────────────────────────
def fast_thinking():
    print("=" * 60)
    print("1. FAST THINKING (no_think)")
    print("=" * 60)

    prompts = [
        "What is the capital of France?",
        "Translate 'Good morning, how are you?' to Japanese.",
        "Summarize the theory of evolution in two sentences.",
    ]

    for prompt in prompts:
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            top_p=1.0,
            max_tokens=256,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )
        elapsed = time.perf_counter() - start

        msg = response.choices[0].message
        thinking = getattr(msg, "reasoning_content", None)
        has_thinking = bool(thinking)

        print(f"\n📝 {prompt}")
        print(f"   Answer:    {msg.content[:120]}{'...' if len(msg.content or '') > 120 else ''}")
        print(f"   Time:      {elapsed:.2f}s")
        print(f"   Tokens:    {response.usage.total_tokens}")
        print(f"   Thinking:  {'Yes (' + str(len(thinking)) + ' chars)' if has_thinking else 'No (direct)'}")


# ──────────────────────────────────────────────────────────────────────
# 2. Deep Reasoning (high) — Chain-of-Thought
# ──────────────────────────────────────────────────────────────────────
def deep_reasoning():
    print("\n" + "=" * 60)
    print("2. DEEP REASONING (high)")
    print("=" * 60)

    prompts = [
        "If a train leaves Boston at 60 mph and another leaves New York at 80 mph, "
        "and the cities are 215 miles apart, when and where do they meet?",
        "Prove that there are infinitely many prime numbers.",
    ]

    for prompt in prompts:
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            top_p=1.0,
            max_tokens=1024,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
        )
        elapsed = time.perf_counter() - start

        msg = response.choices[0].message
        thinking = getattr(msg, "reasoning_content", None)
        content = msg.content or ""

        print(f"\n📝 {prompt[:100]}...")
        if thinking:
            print(f"   🧠 Thinking: {len(thinking)} chars")
            print(f"   💬 Answer:   {len(content)} chars")
            print(f"   ⏱️  Time:     {elapsed:.2f}s")
            print(f"   🔢 Tokens:   {response.usage.total_tokens}")
            print(f"\n   --- Thinking preview ---")
            print(f"   {thinking[:300]}{'...' if len(thinking) > 300 else ''}")
            print(f"\n   --- Answer preview ---")
            print(f"   {content[:300]}{'...' if len(content) > 300 else ''}")
        else:
            print(f"   Answer: {content[:200]}...")
            print(f"   Time:   {elapsed:.2f}s")
            print(f"   Tokens: {response.usage.total_tokens}")


# ──────────────────────────────────────────────────────────────────────
# 3. Side-by-Side Comparison
# ──────────────────────────────────────────────────────────────────────
def compare_modes():
    print("\n" + "=" * 60)
    print("3. FAST vs DEEP — SIDE-BY-SIDE COMPARISON")
    print("=" * 60)

    test_cases = [
        ("Math", "Solve: A rectangle has perimeter 30 and area 54. Find its dimensions."),
        ("Logic", "If all A are B, and some C are not B, can some C be A? Explain."),
        ("Code", "Write a function to check if a string is a valid palindrome, ignoring case and non-alphanumeric chars."),
    ]

    modes = [
        ("no_think", "Fast"),
        ("high", "Deep"),
    ]

    for category, prompt in test_cases:
        print(f"\n{'─' * 60}")
        print(f"📂 Category: {category}")
        print(f"📝 Prompt:   {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

        for effort, label in modes:
            start = time.perf_counter()
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                top_p=1.0,
                max_tokens=512,
                extra_body={"chat_template_kwargs": {"reasoning_effort": effort}},
            )
            elapsed = time.perf_counter() - start

            msg = response.choices[0].message
            thinking = getattr(msg, "reasoning_content", None)
            content = msg.content or ""

            print(f"\n  [{label}]  ⏱️ {elapsed:.2f}s  🔢 {response.usage.total_tokens} tokens  "
                  f"🧠 {'Yes' if thinking else 'No'} thinking")
            print(f"  [{label}]  {content[:150]}{'...' if len(content) > 150 else ''}")


# ──────────────────────────────────────────────────────────────────────
# 4. Streaming with Reasoning
# ──────────────────────────────────────────────────────────────────────
def streaming_reasoning():
    print("\n" + "=" * 60)
    print("4. STREAMING WITH REASONING")
    print("=" * 60)

    prompt = "Explain step by step: why does ice float on water?"
    print(f"\n📝 {prompt}\n")

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        stream=True,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
    )

    in_thinking = False
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta

        # Reasoning content
        if getattr(delta, "reasoning_content", None):
            if not in_thinking:
                print("\n🧠 THINKING: ", end="")
                in_thinking = True
            print(f"\x1b[90m{delta.reasoning_content}\x1b[0m", end="", flush=True)

        # Final answer content
        if delta.content:
            if in_thinking:
                print("\n\n💬 ANSWER: ", end="")
                in_thinking = False
            print(delta.content, end="", flush=True)

    print("\n")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    fast_thinking()
    deep_reasoning()
    compare_modes()
    streaming_reasoning()
