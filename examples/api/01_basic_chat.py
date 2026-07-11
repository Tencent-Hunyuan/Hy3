from __future__ import annotations

from typing import Any

from common import (
    Hy3Config,
    create_client,
    print_json,
    reasoning_extra_body,
    summarize_completion,
)


def build_request(
    config: Hy3Config, messages: list[dict[str, str]]
) -> dict[str, Any]:
    return {
        "model": config.model,
        "messages": [dict(message) for message in messages],
        "temperature": 0.9,
        "top_p": 1.0,
        "max_tokens": 512,
        "extra_body": reasoning_extra_body(config, "no_think"),
    }


def run_conversation(
    client: Any, config: Hy3Config
) -> tuple[dict[str, Any], dict[str, Any]]:
    messages = [
        {"role": "user", "content": "Hello! Briefly introduce yourself."}
    ]

    single_turn_request = build_request(config, messages)
    print_json("Single-turn request", single_turn_request)
    first_completion = client.chat.completions.create(**single_turn_request)
    first = summarize_completion(first_completion)
    print_json("Single-turn response", first)

    messages.extend(
        [
            {"role": "assistant", "content": first["content"]},
            {
                "role": "user",
                "content": "What kinds of tasks can you help me with?",
            },
        ]
    )
    multi_turn_request = build_request(config, messages)
    print_json("Multi-turn request", multi_turn_request)
    second_completion = client.chat.completions.create(**multi_turn_request)
    second = summarize_completion(second_completion)
    print_json("Multi-turn response", second)

    return first, second


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    run_conversation(client, config)


if __name__ == "__main__":
    main()
