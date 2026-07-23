"""Hy3 API example 03: compare non-streaming latency with streaming TTFT."""

from __future__ import annotations

import os
import statistics
import time
from dataclasses import dataclass
from typing import Any

from hy3_client import Hy3Config, create_client, reasoning_options, stream_fragments


@dataclass(frozen=True)
class Timings:
    first_token: float | None
    total: float


def non_streaming_run(client: Any, request: dict[str, Any]) -> Timings:
    started = time.perf_counter()
    client.chat.completions.create(**request, stream=False)
    return Timings(first_token=None, total=time.perf_counter() - started)


def streaming_run(client: Any, request: dict[str, Any]) -> Timings:
    started = time.perf_counter()
    chunks = client.chat.completions.create(**request, stream=True)
    first_token: float | None = None
    for _, answer_delta in stream_fragments(chunks):
        if answer_delta and first_token is None:
            first_token = time.perf_counter() - started
    return Timings(first_token=first_token, total=time.perf_counter() - started)


def average(values: list[float]) -> float:
    return statistics.fmean(values) if values else float("nan")


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    runs = int(os.getenv("HY3_BENCH_RUNS", "3"))
    if runs < 1:
        raise ValueError("HY3_BENCH_RUNS must be at least 1")

    request = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": "Explain idempotency in HTTP APIs in about 120 words.",
            }
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 256,
        "extra_body": reasoning_options("no_think"),
    }

    non_stream_results: list[Timings] = []
    stream_results: list[Timings] = []
    print(f"Target: {config.safe_summary()}; runs per mode={runs}")
    for index in range(1, runs + 1):
        non_stream = non_streaming_run(client, request)
        stream = streaming_run(client, request)
        non_stream_results.append(non_stream)
        stream_results.append(stream)
        ttft = "n/a" if stream.first_token is None else f"{stream.first_token:.3f}s"
        print(
            f"Run {index}: non-stream total={non_stream.total:.3f}s; "
            f"stream TTFT={ttft}, total={stream.total:.3f}s"
        )

    ttfts = [item.first_token for item in stream_results if item.first_token is not None]
    print("\nAverages")
    print(f"Non-stream total: {average([item.total for item in non_stream_results]):.3f}s")
    print(f"Stream TTFT: {average(ttfts):.3f}s")
    print(f"Stream total: {average([item.total for item in stream_results]):.3f}s")
    print("Note: results include client/network/server time and are not a model-only benchmark.")


if __name__ == "__main__":
    main()
