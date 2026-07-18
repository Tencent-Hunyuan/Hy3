"""Hy3 Example 01: Single-turn / Multi-turn Chat.

Demonstrates:
1. Single-turn chat: send one user message and print the reply.
2. Multi-turn chat: pass a system / user / assistant / user history and call again.

Works with local vLLM/SGLang or cloud TokenHub (set HY3_BASE_URL / HY3_API_KEY).
"""

from __future__ import annotations

import os
import sys

# Allow `python examples/en/01_basic_chat.py` from repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import chat_completion, extract_reasoning_and_content, get_config, make_client  # noqa: E402


def single_turn(client):
    print("=" * 60)
    print("[Single-turn Chat]")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "用一句话介绍腾讯混元 Hy3 模型。"},
    ]
    response = chat_completion(client, messages, reasoning="no_think")
    _, content = extract_reasoning_and_content(response.choices[0].message)

    print(f"User: {messages[0]['content']}")
    print(f"Assistant: {content}")
    if response.usage:
        print(
            f"Usage: prompt={response.usage.prompt_tokens} "
            f"completion={response.usage.completion_tokens} "
            f"total={response.usage.total_tokens}"
        )
    print()


def multi_turn(client):
    print("=" * 60)
    print("[Multi-turn Chat]")
    print("=" * 60)

    messages = [
        {"role": "system", "content": "你是一个简洁友好的中文助手。"},
        {"role": "user", "content": "Hy3 的上下文长度是多少？"},
        {"role": "assistant", "content": "Hy3 的上下文长度为 256K tokens。"},
        {"role": "user", "content": "那它的激活参数量是多少？"},
    ]
    response = chat_completion(client, messages, reasoning="no_think")
    _, content = extract_reasoning_and_content(response.choices[0].message)

    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    print(f"assistant: {content}")
    print()


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()
    single_turn(client)
    multi_turn(client)


if __name__ == "__main__":
    main()
