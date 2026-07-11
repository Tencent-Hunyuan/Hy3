from __future__ import annotations

from typing import Any, Iterable

from common import (
    Hy3Config,
    StreamAccumulator,
    StreamResult,
    create_client,
    print_json,
    reasoning_extra_body,
)


def build_request(config: Hy3Config) -> dict[str, Any]:
    return {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": "Explain what an API is in two sentences.",
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "max_tokens": 512,
        "stream": True,
        "stream_options": {"include_usage": True},
        "extra_body": reasoning_extra_body(config, "no_think"),
    }


def consume_stream(chunks: Iterable[Any]) -> StreamResult:
    accumulator = StreamAccumulator()
    print("Content: ", end="", flush=True)

    for chunk in chunks:
        update = accumulator.add_chunk(chunk)
        if update.content:
            print(update.content, end="", flush=True)

    print()
    result = accumulator.result()
    print_json("Stream summary", result)
    return result


def run_streaming(client: Any, config: Hy3Config) -> StreamResult:
    request = build_request(config)
    print_json("Streaming request", request)
    chunks = client.chat.completions.create(**request)
    return consume_stream(chunks)


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    run_streaming(client, config)


if __name__ == "__main__":
    main()
