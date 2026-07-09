"""Hy3 Example 01: Single-turn / Multi-turn Chat.

Calls a locally deployed Hy3 model via the OpenAI-compatible API. Demonstrates:
1. Single-turn chat: send one user message and print the reply.
2. Multi-turn chat: pass a system / user / assistant / user history and call again,
   showing how context carries over to the next turn.

Connection info is read from environment variables, falling back to the default
local service address when unset.
"""

import os

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"


def chat(messages):
    """Wrap a single chat request with the recommended params and thinking disabled."""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )


def single_turn():
    """Single-turn chat: contains only one user message."""
    print("=" * 60)
    print("[Single-turn Chat]")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "用一句话介绍腾讯混元 Hy3 模型。"},
    ]
    response = chat(messages)

    print(f"User: {messages[0]['content']}")
    print(f"Assistant: {response.choices[0].message.content}")
    print()


def multi_turn():
    """Multi-turn chat: append the previous assistant reply to messages and call again."""
    print("=" * 60)
    print("[Multi-turn Chat]")
    print("=" * 60)

    messages = [
        {"role": "system", "content": "你是一个简洁友好的中文助手。"},
        {"role": "user", "content": "Hy3 的上下文长度是多少？"},
        {"role": "assistant", "content": "Hy3 的上下文长度为 256K tokens。"},
        {"role": "user", "content": "那它的激活参数量是多少？"},
    ]
    response = chat(messages)

    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    print(f"assistant: {response.choices[0].message.content}")
    print()


if __name__ == "__main__":
    single_turn()
    multi_turn()
