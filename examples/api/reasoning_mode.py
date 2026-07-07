#!/usr/bin/env python3
"""Compare Hy3 direct mode and reasoning mode.

Environment:
  HY3_BASE_URL=http://127.0.0.1:8000/v1
  HY3_API_KEY=EMPTY
  HY3_MODEL=hy3

Run:
  python3 examples/api/reasoning_mode.py

Sample output:
  reasoning_effort: no_think
  reasoning_content: <not exposed>
  answer: ...

  reasoning_effort: high
  reasoning_content_chars: 936
  answer: ...
"""

from __future__ import annotations

from openai import OpenAI

from common import MODEL, make_client, print_json, print_runtime_config, request_options


def run_once(client: OpenAI, reasoning_effort: str) -> None:
    request = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": (
                    "A service has 3 replicas. Each handles 18 requests per second. "
                    "Traffic is 41 requests per second. Is there enough capacity?"
                ),
            }
        ],
        "temperature": 0.2,
        "top_p": 1.0,
        "max_tokens": 512,
        **request_options(reasoning_effort=reasoning_effort),
    }

    print_json(f"{reasoning_effort} request", request)
    response = client.chat.completions.create(**request)
    choice = response.choices[0]
    message = choice.message
    reasoning_content = getattr(message, "reasoning_content", None) or getattr(
        message, "reasoning", None
    )
    reasoning_details = getattr(message, "reasoning_details", None)

    print(f"\n=== reasoning_effort: {reasoning_effort} ===")
    print("finish_reason:", choice.finish_reason)
    if reasoning_content:
        print("reasoning_content_chars:", len(reasoning_content))
        print("reasoning_content_preview:", reasoning_content[:500])
    else:
        print("reasoning_content: <not exposed>")
    if reasoning_details:
        print_json("reasoning_details", reasoning_details)
    print("answer:", message.content)
    if response.usage:
        print_json(f"{reasoning_effort} usage", response.usage)


def main() -> None:
    print_runtime_config()
    client = make_client()
    run_once(client, "no_think")
    run_once(client, "high")


if __name__ == "__main__":
    main()
