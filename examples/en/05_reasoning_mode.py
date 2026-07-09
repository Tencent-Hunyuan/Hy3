"""
Hy3 Reasoning Mode Comparison Example
=====================================

Demonstrates toggling Hy3's reasoning mode via the thinking switch, comparing two modes:
  - Thinking disabled: respond directly without chain-of-thought (suitable for everyday chat)
  - Thinking enabled: deep chain-of-thought reasoning, suitable for math/code/complex reasoning tasks

How the reasoning switch is passed depends on the deployment. This example sends both
parameter forms for compatibility:
  - Cloud TokenHub API: extra_body={"thinking": {"type": "enabled"|"disabled"}}
  - Local vLLM/SGLang deployment: extra_body={"chat_template_kwargs": {"reasoning_effort": "high"|"no_think"}}

When thinking is enabled, the response returns the chain-of-thought (CoT) in the
message.reasoning_content field, and the final answer in message.content.
  - Cloud: reasoning_content is auto-separated by the TokenHub API
  - Local: requires the server to enable a reasoning parser (vLLM: --reasoning-parser hy_v3; SGLang: --reasoning-parser hunyuan)

Connection info is configured via environment variables (with defaults):
  HY3_BASE_URL  default http://127.0.0.1:8000/v1
  HY3_API_KEY   default EMPTY
"""

import os

from openai import OpenAI

# Initialize the client via environment variables (with defaults) for easy deployment switching
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"

# A prompt well-suited to triggering reasoning: a step-by-step analysis problem with simple arithmetic
PROMPT = "小明有 5 个苹果，分给 3 个朋友每人 1 个，又买了 2 个，现在他还有几个苹果？请逐步分析。"


def chat(enable_thinking: bool):
    """Call Hy3 with the specified reasoning mode and return the full message object.

    Sends both thinking (cloud TokenHub) and chat_template_kwargs.reasoning_effort
    (local vLLM/SGLang) parameter sets for local/cloud compatibility:
      - Cloud recognizes thinking; local ignores that field
      - Local recognizes chat_template_kwargs.reasoning_effort; cloud ignores that field
    """
    thinking_type = "enabled" if enable_thinking else "disabled"
    reasoning_effort = "high" if enable_thinking else "no_think"
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        extra_body={
            # Reasoning switch for the cloud TokenHub API
            "thinking": {"type": thinking_type},
            # Reasoning-depth switch for local vLLM/SGLang deployment
            "chat_template_kwargs": {"reasoning_effort": reasoning_effort},
        },
    )
    return response.choices[0].message


def print_section(title, message):
    """Uniformly print the reasoning_content (if any) and content of a call."""
    print("=" * 70)
    print(title)
    print("=" * 70)
    print(f"[User Question]\n{PROMPT}\n")

    # reasoning_content is an optional field: returns the chain-of-thought when thinking is enabled
    reasoning_content = getattr(message, "reasoning_content", None)
    if reasoning_content:
        print("[Chain-of-thought reasoning_content]")
        print(reasoning_content)
        print()
    else:
        print("[Chain-of-thought reasoning_content] (none; thinking disabled or server did not enable a reasoning parser)\n")

    print("[Final answer content]")
    print(message.content)
    print()


def main():
    # ---- Call 1: thinking disabled, respond directly ----
    msg_off = chat(enable_thinking=False)
    print_section("Mode 1: Thinking disabled (thinking: disabled / reasoning_effort: no_think)", msg_off)

    # ---- Call 2: thinking enabled, deep chain-of-thought ----
    msg_on = chat(enable_thinking=True)
    print_section("Mode 2: Thinking enabled (thinking: enabled / reasoning_effort: high)", msg_on)

    # ---- Comparison summary ----
    print("=" * 70)
    print("[Comparison summary]")
    print("=" * 70)
    print("Thinking disabled: gives the answer directly with no chain-of-thought; fast response, suitable for everyday chat.")
    print("Thinking enabled: outputs step-by-step reasoning (reasoning_content) first, then the final answer,")
    print("          suitable for math/code/complex logic reasoning tasks.")
    print()
    print("Tip: If reasoning_content is still empty when thinking is enabled, please verify:")
    print("  - Cloud TokenHub API: use the thinking parameter (already included in this example)")
    print("  - Local vLLM:   add --reasoning-parser hy_v3 at startup")
    print("  - Local SGLang: add --reasoning-parser hunyuan at startup")


if __name__ == "__main__":
    main()
