"""Hy3 API example 02: parse reasoning and answer deltas from a stream."""

from __future__ import annotations

import time

from hy3_client import Hy3Config, create_client, reasoning_options, stream_fragments


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    print(f"Connecting with {config.safe_summary()}")

    request = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": "Write a four-line checklist for reviewing an API integration.",
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "max_tokens": 512,
        "stream": True,
        "extra_body": reasoning_options("low"),
    }

    started = time.perf_counter()
    chunks = client.chat.completions.create(**request)
    first_answer_at: float | None = None
    reasoning_parts: list[str] = []
    answer_parts: list[str] = []

    print("\nAssistant: ", end="", flush=True)
    for reasoning_delta, answer_delta in stream_fragments(chunks):
        if reasoning_delta:
            reasoning_parts.append(reasoning_delta)
        if answer_delta:
            if first_answer_at is None:
                first_answer_at = time.perf_counter()
            answer_parts.append(answer_delta)
            print(answer_delta, end="", flush=True)

    finished = time.perf_counter()
    print()
    if first_answer_at is not None:
        print(f"Time to first answer token: {first_answer_at - started:.3f}s")
    else:
        print("Time to first answer token: unavailable (no answer delta received)")
    print(f"Total stream time: {finished - started:.3f}s")
    print(f"Answer characters: {len(''.join(answer_parts))}")
    print(f"Reasoning characters: {len(''.join(reasoning_parts))}")


if __name__ == "__main__":
    main()
