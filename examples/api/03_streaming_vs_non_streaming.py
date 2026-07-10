from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from typing import Any, Callable

from common import Hy3Config, StreamAccumulator, create_client, reasoning_extra_body


@dataclass(frozen=True)
class NonStreamingTiming:
    total_seconds: float


@dataclass(frozen=True)
class StreamingTiming:
    first_output_seconds: float | None
    first_content_seconds: float | None
    total_seconds: float


def measure_non_streaming(
    client: Any,
    request: dict[str, Any],
    *,
    clock: Callable[[], float] = time.perf_counter,
) -> NonStreamingTiming:
    started = clock()
    client.chat.completions.create(**request)
    return NonStreamingTiming(total_seconds=clock() - started)


def measure_streaming(
    client: Any,
    request: dict[str, Any],
    *,
    clock: Callable[[], float] = time.perf_counter,
) -> StreamingTiming:
    started = clock()
    first_output = None
    first_content = None
    accumulator = StreamAccumulator()
    stream_request = {
        **request,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    for chunk in client.chat.completions.create(**stream_request):
        update = accumulator.add_chunk(chunk)
        if update.content or update.reasoning:
            now = clock()
            if first_output is None:
                first_output = now - started
            if update.content and first_content is None:
                first_content = now - started

    return StreamingTiming(
        first_output_seconds=first_output,
        first_content_seconds=first_content,
        total_seconds=clock() - started,
    )


def run_comparison(
    client: Any,
    config: Hy3Config,
    *,
    warmup: bool,
) -> tuple[NonStreamingTiming, StreamingTiming]:
    request = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": "Explain idempotency in APIs in three sentences.",
            }
        ],
        "temperature": 0.9,
        "top_p": 1.0,
        "max_tokens": 256,
        "extra_body": reasoning_extra_body(config, "no_think"),
    }
    if warmup:
        client.chat.completions.create(**request)

    non_streaming = measure_non_streaming(client, request)
    streaming = measure_streaming(client, request)
    print(f"Non-streaming total: {non_streaming.total_seconds:.3f}s")
    first_output = (
        f"{streaming.first_output_seconds:.3f}s"
        if streaming.first_output_seconds is not None
        else "unavailable"
    )
    first_content = (
        f"{streaming.first_content_seconds:.3f}s"
        if streaming.first_content_seconds is not None
        else "unavailable"
    )
    print(f"Streaming first output: {first_output}")
    print(f"Streaming first content: {first_content}")
    print(f"Streaming total: {streaming.total_seconds:.3f}s")
    return non_streaming, streaming


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--warmup",
        action="store_true",
        help="Run one unmeasured warmup request before comparison.",
    )
    args = parser.parse_args()
    config = Hy3Config.from_env()
    run_comparison(create_client(config), config, warmup=args.warmup)


if __name__ == "__main__":
    main()
