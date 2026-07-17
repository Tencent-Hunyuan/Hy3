"""Run single-turn and multi-turn Hy3 hosted API conversations."""

from __future__ import annotations

from common import (
    ApiConfig,
    assistant_message_dict,
    create_chat_completion,
    create_client,
    print_response,
    run_example,
    thinking_body,
)


def main() -> None:
    config = ApiConfig.from_env()
    client = create_client(config)
    shared = {
        "model": config.model,
        "temperature": 0.3,
        "max_tokens": 512,
        "extra_body": thinking_body(False),
    }

    print("=== Single turn ===")
    single = create_chat_completion(
        client,
        messages=[{"role": "user", "content": "用一句话解释什么是 API。"}],
        **shared,
    )
    print_response(single, secrets=[config.api_key])

    print("\n=== Multi turn ===")
    messages: list[dict[str, object]] = [
        {"role": "system", "content": "你是一个简洁、准确的编程助手。"},
        {"role": "user", "content": "Python 列表推导式是什么？"},
    ]
    first = create_chat_completion(client, messages=messages, **shared)
    messages.append(assistant_message_dict(first.choices[0].message))
    messages.append({"role": "user", "content": "给一个只保留偶数的例子。"})
    second = create_chat_completion(client, messages=messages, **shared)
    print_response(second, secrets=[config.api_key])


if __name__ == "__main__":
    run_example(main)
