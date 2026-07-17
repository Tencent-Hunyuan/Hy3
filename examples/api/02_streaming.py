"""Hy3 streaming response and chunk parsing example."""

from __future__ import annotations

import json
from typing import Any, Iterable

from common import create_client, get_extra_field, load_config, usage_dict


def consume_stream(stream: Iterable[Any], *, emit: bool = True) -> dict[str, Any]:
    """Consume all chunks, including an empty-choice usage trailer."""

    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    response_id = None
    model = None
    finish_reason = None
    usage = None
    chunk_count = 0

    for chunk in stream:
        chunk_count += 1
        response_id = getattr(chunk, "id", response_id)
        model = getattr(chunk, "model", model)

        current_usage = usage_dict(chunk)
        if current_usage is not None:
            usage = current_usage

        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue

        choice = choices[0]
        finish_reason = choice.finish_reason or finish_reason
        delta = choice.delta

        reasoning = get_extra_field(delta, "reasoning_content")
        if reasoning:
            reasoning_parts.append(reasoning)
            if emit:
                print(reasoning, end="", flush=True)

        if delta.content:
            content_parts.append(delta.content)
            if emit:
                print(delta.content, end="", flush=True)

    if emit:
        print()
    return {
        "id": response_id,
        "model": model,
        "content": "".join(content_parts),
        "reasoning_content": "".join(reasoning_parts) or None,
        "finish_reason": finish_reason,
        "usage": usage,
        "chunk_count": chunk_count,
    }


def main() -> None:
    config = load_config()
    client = create_client(config)
    request = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": "用 150 字以内解释流式输出适合什么场景。",
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "max_tokens": 512,
        "stream": True,
        "stream_options": {"include_usage": True},
        "extra_body": {"thinking": {"type": "disabled"}},
    }

    printable = {**request, "extra_body": request["extra_body"]}
    print("request:", json.dumps(printable, ensure_ascii=False, indent=2))
    print("\nstreamed content:")
    result = consume_stream(client.chat.completions.create(**request))
    print("\nparsed response:")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
