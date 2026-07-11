import json
import os
import time
from typing import Any

from openai import OpenAI


base_url = os.getenv(
    "HY3_BASE_URL",
    "http://127.0.0.1:8000/v1",
)

api_key = os.getenv(
    "HY3_API_KEY",
    "EMPTY",
)

model = os.getenv(
    "HY3_MODEL",
    "hy3",
)


client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)


def print_request(
    title: str,
    payload: dict[str, Any],
) -> None:
    """Print the complete request payload."""

    print(f"\n=== {title} request ===")
    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )


def run_non_streaming() -> dict[str, Any]:
    """Measure total latency for a non-streaming request."""

    request_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Explain the difference between "
                    "Redis and MySQL in about 150 words."
                ),
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "stream": False,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": "no_think"
            }
        },
    }

    print_request(
        "Non-streaming",
        request_payload,
    )

    start_time = time.perf_counter()

    response = client.chat.completions.create(
        **request_payload
    )

    end_time = time.perf_counter()

    total_latency = end_time - start_time

    print("\n--- Complete response ---")
    print(response.model_dump_json(indent=2))

    content = response.choices[0].message.content

    return {
        "total_latency": total_latency,
        "content": content,
    }


def run_streaming() -> dict[str, Any]:
    """Measure TTFT and total latency for a streaming request."""

    request_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Explain the difference between "
                    "Redis and MySQL in about 150 words."
                ),
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "stream": True,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": "no_think"
            }
        },
    }

    print_request(
        "Streaming",
        request_payload,
    )

    start_time = time.perf_counter()

    stream = client.chat.completions.create(
        **request_payload
    )

    first_token_time = None
    text_parts: list[str] = []
    chunk_count = 0
    finish_reason = None

    print("\n--- Streaming content ---")

    for chunk in stream:
        chunk_count += 1

        if not chunk.choices:
            continue

        choice = chunk.choices[0]
        delta = choice.delta

        if delta.content is not None:
            if first_token_time is None:
                first_token_time = time.perf_counter()

            text_parts.append(delta.content)

            print(
                delta.content,
                end="",
                flush=True,
            )

        if choice.finish_reason is not None:
            finish_reason = choice.finish_reason

    end_time = time.perf_counter()

    print()

    if first_token_time is None:
        ttft = None
    else:
        ttft = first_token_time - start_time

    total_latency = end_time - start_time
    full_content = "".join(text_parts)

    return {
        "ttft": ttft,
        "total_latency": total_latency,
        "chunk_count": chunk_count,
        "finish_reason": finish_reason,
        "content": full_content,
    }


def print_comparison(
    non_streaming_result: dict[str, Any],
    streaming_result: dict[str, Any],
) -> None:
    """Print latency metrics for both request modes."""

    print("\n\n=== Latency comparison ===")

    print("\nNon-streaming:")
    print(
        "Total latency: "
        f"{non_streaming_result['total_latency']:.3f}s"
    )

    print("\nStreaming:")

    ttft = streaming_result["ttft"]

    if ttft is None:
        print("TTFT: unavailable")
    else:
        print(f"TTFT: {ttft:.3f}s")

    print(
        "Total latency: "
        f"{streaming_result['total_latency']:.3f}s"
    )

    print(
        "Chunks received: "
        f"{streaming_result['chunk_count']}"
    )

    print(
        "Finish reason: "
        f"{streaming_result['finish_reason']}"
    )

    print("\nNote:")
    print(
        "Streaming can improve perceived responsiveness "
        "by delivering content before the full response "
        "is complete. It does not guarantee lower total latency."
    )


if __name__ == "__main__":
    non_streaming_result = run_non_streaming()
    streaming_result = run_streaming()

    print_comparison(
        non_streaming_result,
        streaming_result,
    )
