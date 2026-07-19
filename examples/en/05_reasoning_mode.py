"""Hy3 Example 05: Reasoning mode comparison (no_think / low / high).

Sends dual-compatible parameters for local and cloud:
  - Cloud TokenHub: thinking:{type: enabled|disabled}
  - Local vLLM/SGLang: chat_template_kwargs.reasoning_effort (no_think|low|high)

When thinking is enabled, chain-of-thought appears in message.reasoning_content
(local requires --reasoning-parser hy_v3 / hunyuan).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import (  # noqa: E402
    chat_completion,
    extract_reasoning_and_content,
    get_config,
    make_client,
)

PROMPT = "小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。"

MODES = (
    ("no_think", "Mode 1: Thinking off (no_think) — direct answer"),
    ("low", "Mode 2: Light thinking (low)"),
    ("high", "Mode 3: Deep thinking (high)"),
)


def run_mode(client, reasoning: str, title: str):
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"[User Question]\n{PROMPT}\n")

    # high mode can emit long CoT; give it more room
    max_tokens = 8192 if reasoning == "high" else 2048
    response = chat_completion(
        client,
        [{"role": "user", "content": PROMPT}],
        reasoning=reasoning,
        max_tokens=max_tokens,
    )
    message = response.choices[0].message
    reasoning_content, content = extract_reasoning_and_content(message)

    if reasoning_content:
        print("[Chain-of-thought reasoning_content]")
        print(reasoning_content)
        print()
    else:
        print(
            "[Chain-of-thought reasoning_content] "
            "(none; thinking disabled, or server has no reasoning parser)\n"
        )

    print("[Final answer content]")
    print(content)
    if response.usage:
        print(
            f"\n[Usage] prompt={response.usage.prompt_tokens} "
            f"completion={response.usage.completion_tokens} "
            f"total={response.usage.total_tokens}"
        )
    print()


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    for mode, title in MODES:
        run_mode(client, mode, title)

    print("=" * 70)
    print("[Comparison summary]")
    print("=" * 70)
    print("no_think: direct answer, lowest latency — everyday chat.")
    print("low:      light chain-of-thought — structured / multi-constraint tasks.")
    print("high:     deep CoT — math / code / hard reasoning (raise max_tokens).")
    print()
    print("If reasoning_content is empty when thinking is on, check:")
    print("  - Cloud TokenHub: thinking parameter is already sent by common.build_extra_body")
    print("  - Local vLLM:   add --reasoning-parser hy_v3 at startup")
    print("  - Local SGLang: add --reasoning-parser hunyuan at startup")


if __name__ == "__main__":
    main()
