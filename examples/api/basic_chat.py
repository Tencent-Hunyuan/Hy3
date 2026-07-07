#!/usr/bin/env python3
"""Hy3 basic chat example: single-turn and multi-turn.

Environment:
  HY3_BASE_URL=http://127.0.0.1:8000/v1
  HY3_API_KEY=EMPTY
  HY3_MODEL=hy3

Run:
  python3 examples/api/basic_chat.py

Sample output:
  === single_turn parsed response ===
  id: chatcmpl-...
  model: hy3
  finish_reason: stop
  role: assistant
  content: Hy3 is Tencent's MoE language model...
"""

from __future__ import annotations

from typing import Any

from common import MODEL, make_client, print_json, print_runtime_config, request_options


def print_chat_response(label: str, response: Any) -> str:
    choice = response.choices[0]
    message = choice.message
    reasoning_content = getattr(message, "reasoning_content", None) or getattr(
        message, "reasoning", None
    )
    reasoning_details = getattr(message, "reasoning_details", None)

    print(f"\n=== {label} parsed response ===")
    print("id:", response.id)
    print("model:", response.model)
    print("created:", response.created)
    print("finish_reason:", choice.finish_reason)
    print("role:", message.role)
    print("content:", message.content)
    if reasoning_content:
        print("reasoning_content:", reasoning_content)
    if reasoning_details:
        print_json("reasoning_details", reasoning_details)
    if response.usage:
        print_json("usage", response.usage)

    return message.content or ""


def main() -> None:
    print_runtime_config()
    client = make_client()

    single_turn_request = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "Introduce Hy3 in one sentence.",
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "max_tokens": 128,
        **request_options(reasoning_effort="no_think"),
    }

    print_json("single_turn request", single_turn_request)
    single_turn_response = client.chat.completions.create(**single_turn_request)
    assistant_text = print_chat_response("single_turn", single_turn_response)

    multi_turn_messages = list(single_turn_request["messages"])
    multi_turn_messages.append({"role": "assistant", "content": assistant_text})
    multi_turn_messages.append(
        {
            "role": "user",
            "content": "Now give three practical API integration tips.",
        }
    )

    multi_turn_request = {
        "model": MODEL,
        "messages": multi_turn_messages,
        "temperature": 0.7,
        "top_p": 1.0,
        "max_tokens": 256,
        **request_options(reasoning_effort="no_think"),
    }

    print_json("multi_turn request", multi_turn_request)
    multi_turn_response = client.chat.completions.create(**multi_turn_request)
    print_chat_response("multi_turn", multi_turn_response)


if __name__ == "__main__":
    main()
