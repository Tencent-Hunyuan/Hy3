"""Compare non-streaming time-to-visible-response with streaming TTFT."""

from __future__ import annotations

import time
from typing import Any

from common import create_client, get_extra_field, load_config, usage_dict


def run_non_streaming(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    response = client.chat.completions.create(**request)
    elapsed = time.perf_counter() - start
    choice = response.choices[0]
    return {
        "id": response.id,
        "model": response.model,
        "time_to_visible_response_seconds": elapsed,
        "total_seconds": elapsed,
        "content": choice.message.content or "",
        "finish_reason": choice.finish_reason,
        "usage": usage_dict(response),
    }


def run_streaming(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    first_visible = None
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    finish_reason = None
    usage = None
    response_id = None
    model = None

    stream = client.chat.completions.create(
        **request,
        stream=True,
        stream_options={"include_usage": True},
    )
    for chunk in stream:
        response_id = getattr(chunk, "id", response_id)
        model = getattr(chunk, "model", model)
        current_usage = usage_dict(chunk)
        if current_usage is not None:
            usage = current_usage
        if not chunk.choices:
            continue

        choice = chunk.choices[0]
        finish_reason = choice.finish_reason or finish_reason
        reasoning = get_extra_field(choice.delta, "reasoning_content")
        content = choice.delta.content
        if (reasoning or content) and first_visible is None:
            first_visible = time.perf_counter() - start
        if reasoning:
            reasoning_parts.append(reasoning)
        if content:
            content_parts.append(content)

    total = time.perf_counter() - start
    return {
        "id": response_id,
        "model": model,
        "first_visible_chunk_seconds": first_visible,
        "total_seconds": total,
        "content": "".join(content_parts),
        "reasoning_content": "".join(reasoning_parts) or None,
        "finish_reason": finish_reason,
        "usage": usage,
    }


def main() -> None:
    config = load_config()
    client = create_client(config, timeout=120.0)
    request = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": "用不超过 300 字解释 Transformer 的自注意力机制。",
            }
        ],
        "temperature": 0.2,
        "top_p": 1.0,
        "max_tokens": 768,
        "extra_body": {"thinking": {"type": "disabled"}},
    }

    print("Running non-streaming request...")
    non_streaming = run_non_streaming(client, request)
    print("Running streaming request...")
    streaming = run_streaming(client, request)

    print("\n=== Timing comparison ===")
    print(f"non-streaming first visible / total: {non_streaming['total_seconds']:.3f}s")
    ttft = streaming["first_visible_chunk_seconds"]
    print("streaming first visible chunk:", f"{ttft:.3f}s" if ttft else "N/A")
    print("streaming total:", f"{streaming['total_seconds']:.3f}s")
    print("non-streaming id/model:", non_streaming["id"], non_streaming["model"])
    print("streaming id/model:", streaming["id"], streaming["model"])
    print("non-streaming chars:", len(non_streaming["content"]))
    print("streaming chars:", len(streaming["content"]))
    print("non-streaming usage:", non_streaming["usage"])
    print("streaming usage:", streaming["usage"])
    print(
        "\nNote: these are two independent generations, not a scientific benchmark. "
        "Network, queueing, cache state, and output length affect the result."
    )


if __name__ == "__main__":
    main()
