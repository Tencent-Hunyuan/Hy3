"""Hy3 API example 01: single-turn and stateful multi-turn chat."""

from __future__ import annotations

import json
from typing import Any

from hy3_client import Hy3Config, create_client, reasoning_options, split_message


def send_chat(client: Any, config: Hy3Config, messages: list[dict[str, str]]) -> Any:
    request = {
        "model": config.model,
        "messages": messages,
        "temperature": 0.9,
        "top_p": 1.0,
        "max_tokens": 512,
        "extra_body": reasoning_options("no_think"),
    }
    print("Request:\n" + json.dumps(request, ensure_ascii=False, indent=2))
    return client.chat.completions.create(**request)


def print_response(response: Any) -> str:
    choice = response.choices[0]
    reasoning, content = split_message(choice.message)
    print(f"Assistant: {content}")
    print(f"Finish reason: {choice.finish_reason}")
    if reasoning:
        print(f"Reasoning received: {len(reasoning)} characters")
    if response.usage:
        print(
            "Tokens: "
            f"prompt={response.usage.prompt_tokens}, "
            f"completion={response.usage.completion_tokens}, "
            f"total={response.usage.total_tokens}"
        )
    return content


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    print(f"Connecting with {config.safe_summary()}\n")

    print("=== Single turn ===")
    single_messages = [
        {"role": "user", "content": "Give three practical uses for a 256K context window."}
    ]
    print_response(send_chat(client, config, single_messages))

    print("\n=== Multi turn ===")
    history = [
        {"role": "system", "content": "You are a concise API design reviewer."},
        {"role": "user", "content": "Name one benefit of streaming responses."},
    ]
    first_reply = print_response(send_chat(client, config, history))
    history.extend(
        [
            {"role": "assistant", "content": first_reply},
            {"role": "user", "content": "Now name one trade-off, in the same context."},
        ]
    )
    print_response(send_chat(client, config, history))


if __name__ == "__main__":
    main()
