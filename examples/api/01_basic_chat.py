"""Hy3 basic single-turn and multi-turn chat example."""

from __future__ import annotations

import json
from typing import Any

from common import create_client, load_config, usage_dict


def response_details(response: Any) -> dict[str, Any]:
    """Parse the complete non-streaming response fields used by this example."""

    if not response.choices:
        raise RuntimeError("The API returned no choices")
    choice = response.choices[0]
    return {
        "id": response.id,
        "model": response.model,
        "content": choice.message.content,
        "finish_reason": choice.finish_reason,
        "usage": usage_dict(response),
    }


def create_chat_completion(
    client: Any, model: str, messages: list[dict[str, Any]]
) -> Any:
    """Send one complete chat request with thinking disabled."""

    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        extra_body={"thinking": {"type": "disabled"}},
    )


def main() -> None:
    config = load_config()
    client = create_client(config)

    print("=== Single-turn chat ===")
    single_messages = [{"role": "user", "content": "请用三点说明什么是混合专家模型。"}]
    print("request messages:", json.dumps(single_messages, ensure_ascii=False))
    single = response_details(
        create_chat_completion(client, config.model, single_messages)
    )
    print("id:", single["id"], "model:", single["model"])
    print("assistant:", single["content"])
    print("finish_reason:", single["finish_reason"])
    print("usage:", single["usage"])

    print("\n=== Multi-turn chat ===")
    history: list[dict[str, Any]] = [
        {"role": "user", "content": "给我推荐一个学习 Python 的三步计划。"}
    ]
    first = response_details(create_chat_completion(client, config.model, history))
    print("round 1 assistant:", first["content"])
    history.append({"role": "assistant", "content": first["content"]})
    history.append({"role": "user", "content": "把第二步展开成一个为期 7 天的安排。"})

    second = response_details(create_chat_completion(client, config.model, history))
    print("id:", second["id"], "model:", second["model"])
    print("round 2 assistant:", second["content"])
    print("finish_reason:", second["finish_reason"])
    print("usage:", second["usage"])


if __name__ == "__main__":
    main()
