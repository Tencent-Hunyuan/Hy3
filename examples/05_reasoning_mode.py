"""
05_reasoning_mode.py — Hy3 Reasoning Mode Comparison Example
=============================================================
Demo: Compare effects of no_think vs low vs high reasoning depth

Run:
    python 05_reasoning_mode.py

Environment Variables:
    HY3_BASE_URL  - API endpoint (default: http://127.0.0.1:8000/v1)
    HY3_API_KEY   - API key (default: EMPTY)
    HY3_MODEL     - Model name (default: hy3)

Note:
    Cloud API (e.g., tokenhub.tencentmaas.com) uses:
        extra_body={"reasoning_effort": ...}
    Self-hosted (vLLM/SGLang) uses:
        extra_body={"chat_template_kwargs": {"reasoning_effort": ...}}
    This example auto-detects both modes.
"""

import os
import time
from openai import OpenAI

# ── Configuration ────────────────────────────────────────
BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# Auto-detect cloud API (non-localhost is considered cloud)
IS_CLOUD_API = "127.0.0.1" not in BASE_URL and "localhost" not in BASE_URL


def build_reasoning_body(effort: str) -> dict:
    """
    Build extra_body parameters based on deployment type

    Cloud API format:
        extra_body={"reasoning_effort": "high"}

    Self-hosted format (vLLM/SGLang):
        extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}
    """
    if IS_CLOUD_API:
        return {"reasoning_effort": effort}
    else:
        return {"chat_template_kwargs": {"reasoning_effort": effort}}


def request_with_reasoning(prompt: str, effort: str, max_tokens: int = 2048) -> dict:
    """
    Send request with specified reasoning depth

    Args:
        prompt: User input
        effort: Reasoning depth - "no_think" | "low" | "high"
        max_tokens: Maximum tokens to generate

    Returns:
        Dict with response content and performance metrics
    """
    start = time.time()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=max_tokens,
        extra_body=build_reasoning_body(effort),
    )

    end = time.time()
    message = response.choices[0].message

    return {
        "effort": effort,
        "content": message.content or "",
        "reasoning_content": getattr(message, "reasoning_content", None) or "",
        "duration": end - start,
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }


# ══════════════════════════════════════════════════════
# Example 1: Simple Q&A — no_think vs high
# ══════════════════════════════════════════════════════
def compare_simple_qa():
    """Simple question: no_think answers directly, high thinks first"""
    print("=" * 60)
    print("Example 1: Simple Q&A Comparison")
    print("=" * 60)

    prompt = "What is the capital of China?"
    print(f"\n[User]: {prompt}\n")

    for effort in ["no_think", "high"]:
        print(f"--- reasoning_effort: {effort} ---")
        result = request_with_reasoning(prompt, effort, max_tokens=256)

        print(f"Answer: {result['content'][:200]}")
        if result["reasoning_content"]:
            print(f"Reasoning: {result['reasoning_content'][:200]}")
        else:
            print(f"Reasoning: (None, direct answer)")
        print(f"Duration: {result['duration']:.3f}s | "
              f"Tokens: {result['completion_tokens']}\n")


# ══════════════════════════════════════════════════════
# Example 2: Math reasoning — three-level comparison
# ══════════════════════════════════════════════════════
def compare_math_reasoning():
    """Math problem: show the impact of reasoning depth on problem-solving"""
    print("\n" + "=" * 60)
    print("Example 2: Math Reasoning 3-level Comparison")
    print("=" * 60)

    prompt = (
        "A pool has two pipes. Pipe A fills it in 6 hours, "
        "Pipe B in 4 hours. If both are opened but B is closed "
        "after 1 hour, how long does it take to fill the pool?"
    )
    print(f"\n[User]: {prompt}\n")

    results = []
    for effort in ["no_think", "low", "high"]:
        print(f"--- reasoning_effort: {effort} ---")
        result = request_with_reasoning(prompt, effort)
        results.append(result)

        # Truncate display (avoid excessive output)
        content_preview = result["content"][:300]
        reasoning_preview = (
            result["reasoning_content"][:300]
            if result["reasoning_content"]
            else "(No reasoning process)"
        )

        print(f"Answer:\n{content_preview}")
        print(f"\nReasoning:\n{reasoning_preview}")
        print(f"\nDuration: {result['duration']:.3f}s | "
              f"Tokens: {result['completion_tokens']}\n")

    # Summary table
    print("--- Summary Comparison ---")
    print(f"{'Level':<14} {'Duration(s)':<14} {'Tokens':<10} {'Has Reasoning':<16}")
    print("-" * 54)
    for r in results:
        has_reasoning = "Yes" if r["reasoning_content"] else "No"
        print(f"{r['effort']:<14} {r['duration']:<14.3f} "
              f"{r['completion_tokens']:<10} {has_reasoning:<16}")


# ══════════════════════════════════════════════════════
# Example 3: Code generation — advantage of reasoning mode
# ══════════════════════════════════════════════════════
def compare_code_generation():
    """Code generation: reasoning mode helps produce more correct code"""
    print("\n" + "=" * 60)
    print("Example 3: Code Generation Comparison")
    print("=" * 60)

    prompt = (
        "Implement an LRU Cache in Python with O(1) get and put operations. "
        "Include complete code and usage examples."
    )
    print(f"\n[User]: {prompt}\n")

    for effort in ["no_think", "high"]:
        print(f"--- reasoning_effort: {effort} ---")
        result = request_with_reasoning(prompt, effort, max_tokens=4096)

        # Count code lines
        code_lines = [l for l in result["content"].split("\n")
                      if l.strip().startswith(("def ", "class ", "import ", "from "))]
        print(f"Answer length: {len(result['content'])} chars")
        print(f"Function/class definitions: {len(code_lines)}")
        if result["reasoning_content"]:
            print(f"Reasoning length: {len(result['reasoning_content'])} chars")
        print(f"Duration: {result['duration']:.3f}s | "
              f"Tokens: {result['completion_tokens']}\n")

    # Usage recommendations
    print("--- Recommendations ---")
    print("  no_think: Simple Q&A, daily chat, formatted output")
    print("  low:      Basic logic, simple classification, format conversion")
    print("  high:     Math reasoning, complex coding, multi-step analysis, strategy")


# ══════════════════════════════════════════════════════
# Example 4: Streaming + reasoning mode
# ══════════════════════════════════════════════════════
def streaming_with_reasoning():
    """Stream output of reasoning process and final answer"""
    print("\n" + "=" * 60)
    print("Example 4: Streaming Reasoning Mode")
    print("=" * 60)

    prompt = "Prove that for any positive integer n, 1+2+...+n = n(n+1)/2"
    print(f"\n[User]: {prompt}")

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=2048,
        stream=True,
        extra_body=build_reasoning_body("high"),
    )

    print("\n[Assistant - Streaming Output]:")
    full_content = ""
    reasoning_content = ""

    for chunk in stream:
        delta = chunk.choices[0].delta
        # Some APIs return reasoning process via reasoning_content field in streaming
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            reasoning_content += delta.reasoning_content
        if hasattr(delta, "content") and delta.content:
            print(delta.content, end="", flush=True)
            full_content += delta.content

    print(f"\n\n--- Streaming Reasoning Complete ---")
    print(f"Answer chars: {len(full_content)}")
    if reasoning_content:
        print(f"Reasoning chars: {len(reasoning_content)}")
        print(f"Reasoning preview: {reasoning_content[:200]}...")


# ── Main entry ───────────────────────────────────────────
if __name__ == "__main__":
    api_type = "Cloud API" if IS_CLOUD_API else "Self-hosted"
    print("Hy3 Reasoning Mode Comparison Example")
    print(f"API: {BASE_URL} | Model: {MODEL} | Type: {api_type}\n")

    compare_simple_qa()
    compare_math_reasoning()
    compare_code_generation()
    streaming_with_reasoning()

    print("\n" + "=" * 60)
    print("All reasoning mode examples completed!")
    print("=" * 60)
