import json
import os
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


def print_request(payload: dict[str, Any]) -> None:
    """Print the complete request payload."""

    print("=== Request ===")
    print(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
    )


def streaming_chat() -> None:
    """Run a streaming chat completion and parse every chunk."""

    request_payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Explain what an API is in about "
                    "three short sentences."
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

    print_request(request_payload)

    stream = client.chat.completions.create(
        **request_payload
    )

    text_parts: list[str] = []
    chunk_count = 0
    finish_reason = None

    print("\n=== Streaming chunks ===")

    for chunk in stream:
        chunk_count += 1

        print(f"\n--- Chunk {chunk_count} ---")
        print(chunk.model_dump_json(indent=2))

        # Some compatible endpoints may emit chunks
        # without any choices.
        if not chunk.choices:
            continue

        choice = chunk.choices[0]
        delta = choice.delta

        if delta.content is not None:
            text_parts.append(delta.content)

            print(
                "Parsed delta.content: "
                f"{delta.content!r}"
            )

        if choice.finish_reason is not None:
            finish_reason = choice.finish_reason

    full_text = "".join(text_parts)

    print("\n=== Final parsed result ===")
    print(f"Chunks received: {chunk_count}")
    print(f"Finish reason: {finish_reason}")
    print(f"Full content: {full_text}")


if __name__ == "__main__":
    streaming_chat()
