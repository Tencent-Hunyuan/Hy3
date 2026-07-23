"""
Example 1: Basic Chat — single-turn and multi-turn conversations with Hy3.

Usage:
    python 01-basic-chat.py

Prerequisites:
    - Hy3 server running at http://127.0.0.1:8000 (vLLM or SGLang)
    - pip install openai
"""

from openai import OpenAI

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


# ──────────────────────────────────────────────────────────────────────
# 1. Single-Turn Chat
# ──────────────────────────────────────────────────────────────────────
def single_turn():
    print("=" * 60)
    print("1. SINGLE-TURN CHAT")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Explain quantum computing in one paragraph."},
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=256,
    )

    message = response.choices[0].message
    finish_reason = response.choices[0].finish_reason

    print(f"\nRole: {message.role}")
    print(f"Content:\n{message.content}")
    print(f"\nFinish reason: {finish_reason}")
    print(f"Prompt tokens:   {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    print(f"Total tokens:    {response.usage.total_tokens}")

    if finish_reason == "length":
        print("\n⚠️  Response was truncated — consider increasing max_tokens.")


# ──────────────────────────────────────────────────────────────────────
# 2. Multi-Turn Chat
# ──────────────────────────────────────────────────────────────────────
def multi_turn():
    print("\n" + "=" * 60)
    print("2. MULTI-TURN CHAT")
    print("=" * 60)

    messages = [
        {
            "role": "system",
            "content": "You are a helpful physics tutor. Keep explanations concise but thorough.",
        },
    ]

    questions = [
        "What is quantum entanglement?",
        "Can you give a real-world analogy for that?",
        "How is this used in quantum computing?",
    ]

    for i, question in enumerate(questions, 1):
        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.9,
            top_p=1.0,
            max_tokens=300,
        )

        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})

        print(f"\n--- Turn {i} ---")
        print(f"User: {question}")
        print(f"Assistant: {reply[:200]}{'...' if len(reply) > 200 else ''}")
        print(f"(Tokens this turn: {response.usage.total_tokens})")


# ──────────────────────────────────────────────────────────────────────
# 3. Helper Function for Reusable Chat
# ──────────────────────────────────────────────────────────────────────
def chat_turn(messages: list, user_input: str) -> str:
    """Send a user message and return the assistant's reply, updating history in place."""
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
    )

    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    return reply


def reusable_chat():
    print("\n" + "=" * 60)
    print("3. REUSABLE CHAT HELPER")
    print("=" * 60)

    messages = []
    turns = [
        "What is a black hole?",
        "How big can they get?",
    ]

    for i, question in enumerate(turns, 1):
        reply = chat_turn(messages, question)
        print(f"\n--- Turn {i} ---")
        print(f"Q: {question}")
        print(f"A: {reply[:250]}{'...' if len(reply) > 250 else ''}")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    single_turn()
    multi_turn()
    reusable_chat()
