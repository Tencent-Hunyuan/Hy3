"""
01_basic_chat.py — Hy3 Basic Chat Example
==========================================
Demo: Single-turn conversation + Multi-turn conversation + System Prompt configuration

Run:
    python 01_basic_chat.py

Environment Variables:
    HY3_BASE_URL  - API endpoint (default: http://127.0.0.1:8000/v1)
    HY3_API_KEY   - API key (default: EMPTY)
    HY3_MODEL     - Model name (default: hy3)
"""

import os
from openai import OpenAI

# ── Configuration ────────────────────────────────────────
BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ══════════════════════════════════════════════════════
# Example 1: Single-turn conversation
# ══════════════════════════════════════════════════════
def single_turn_chat():
    """Simplest single-turn Q&A"""
    print("=" * 60)
    print("Example 1: Single-turn Chat")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Introduce the Hy3 model in one sentence."}
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=256,
    )

    # Parse response
    message = response.choices[0].message
    print(f"\n[User]: Introduce the Hy3 model in one sentence.")
    print(f"[Assistant]: {message.content}")
    print(f"\n--- Response Details ---")
    print(f"Finish Reason: {response.choices[0].finish_reason}")
    print(f"Token Usage: prompt={response.usage.prompt_tokens}, "
          f"completion={response.usage.completion_tokens}, "
          f"total={response.usage.total_tokens}")
    return response


# ══════════════════════════════════════════════════════
# Example 2: Multi-turn chat (with context memory)
# ══════════════════════════════════════════════════════
def multi_turn_chat():
    """Multi-turn chat, demonstrating how the model remembers context"""
    print("\n" + "=" * 60)
    print("Example 2: Multi-turn Chat")
    print("=" * 60)

    # Conversation history
    messages = [
        {"role": "system", "content": "You are a professional technical advisor. Be concise and professional."},
    ]

    # Multi-turn questions, each depending on the previous context
    conversation = [
        ("What is MoE architecture?", None),
        ("What are the features of Hy3's MoE architecture?", None),
        ("How does it differ from GPT-4's architecture?", None),
    ]

    for i, (user_msg, _) in enumerate(conversation, 1):
        messages.append({"role": "user", "content": user_msg})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.9,
            top_p=1.0,
            max_tokens=512,
        )

        assistant_msg = response.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_msg})

        print(f"\n[Turn {i}]")
        print(f"[User]: {user_msg}")
        print(f"[Assistant]: {assistant_msg}")
        print(f"  (tokens: {response.usage.total_tokens})")

    return messages


# ══════════════════════════════════════════════════════
# Example 3: System Prompt to control output format
# ══════════════════════════════════════════════════════
def system_prompt_example():
    """Use System Prompt to precisely control output format"""
    print("\n" + "=" * 60)
    print("Example 3: System Prompt Controls Output Format")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a JSON data generator. The user will give you a topic, "
                    "and you need to return a JSON array with 3 entries. "
                    "Each entry should have name, description, and score fields. "
                    "Return only JSON, no other text."
                ),
            },
            {"role": "user", "content": "Recommend programming languages"},
        ],
        temperature=0.7,
        max_tokens=512,
    )

    print(f"\n[User]: Recommend programming languages")
    print(f"[Assistant]:\n{response.choices[0].message.content}")
    return response


# ── Main entry ───────────────────────────────────────────
if __name__ == "__main__":
    print("Hy3 Basic Chat Example")
    print(f"API: {BASE_URL} | Model: {MODEL}\n")

    single_turn_chat()
    multi_turn_chat()
    system_prompt_example()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
