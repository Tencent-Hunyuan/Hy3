"""Compare repeated client-observed non-streaming and streaming latency."""

from __future__ import annotations

import argparse
import json
import math
import time
from typing import Any

from common import (
    ApiConfig,
    aggregate_stream,
    create_chat_completion,
    create_client,
    get_field,
    run_example,
    thinking_body,
)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def usage_total_tokens(value: Any) -> int | None:
    usage = get_field(value, "usage")
    return get_field(usage, "total_tokens") if usage is not None else None


def measure_non_streaming(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    transient_retries = 0

    def observe_retry(_attempt: int, _error: BaseException, _delay: float) -> None:
        nonlocal transient_retries
        transient_retries += 1

    started = time.perf_counter()
    response = create_chat_completion(client, on_retry=observe_retry, **request)
    elapsed = time.perf_counter() - started
    choice = response.choices[0]
    return {
        "total_seconds": elapsed,
        "finish_reason": choice.finish_reason,
        "total_tokens": usage_total_tokens(response),
        "transient_retries": transient_retries,
    }


def measure_streaming(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    first_content_at: float | None = None
    transient_retries = 0

    def observe_content(_text: str) -> None:
        nonlocal first_content_at
        if first_content_at is None:
            first_content_at = time.perf_counter()

    def observe_retry(_attempt: int, _error: BaseException, _delay: float) -> None:
        nonlocal transient_retries
        transient_retries += 1

    stream = create_chat_completion(
        client,
        on_retry=observe_retry,
        **request,
        stream=True,
        stream_options={"include_usage": True},
    )
    result = aggregate_stream(stream, on_content=observe_content)
    ended = time.perf_counter()
    return {
        "ttft_seconds": (
            first_content_at - started if first_content_at is not None else None
        ),
        "total_seconds": ended - started,
        "finish_reason": result.finish_reason,
        "total_tokens": get_field(result.usage, "total_tokens"),
        "complete": result.complete,
        "transient_retries": transient_retries,
    }


def summary(rows: list[dict[str, Any]], field: str) -> dict[str, float] | None:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    if not values:
        return None
    return {
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs", type=int, default=5, help="measured pairs (default: 5)"
    )
    parser.add_argument(
        "--warmup", type=int, default=1, help="warm-up pairs (default: 1)"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.runs < 2 or args.warmup < 0:
        raise SystemExit("--runs must be at least 2 and --warmup cannot be negative")

    config = ApiConfig.from_env()
    client = create_client(config)
    request: dict[str, Any] = {
        "model": config.model,
        "messages": [{"role": "user", "content": "用三句话解释二分查找。"}],
        "temperature": 0,
        "max_tokens": 512,
        "extra_body": thinking_body(False),
    }

    for _ in range(args.warmup):
        measure_non_streaming(client, request)
        measure_streaming(client, request)

    non_streaming: list[dict[str, Any]] = []
    streaming: list[dict[str, Any]] = []
    for _ in range(args.runs):
        non_streaming.append(measure_non_streaming(client, request))
        streaming.append(measure_streaming(client, request))

    report = {
        "model": config.model,
        "note": (
            "Client-observed samples include any reported transient retry wait; "
            "they are not a service SLA or quality comparison."
        ),
        "warmup_pairs": args.warmup,
        "measured_pairs": args.runs,
        "non_streaming": {
            "samples": non_streaming,
            "total_seconds": summary(non_streaming, "total_seconds"),
        },
        "streaming": {
            "samples": streaming,
            "ttft_seconds": summary(streaming, "ttft_seconds"),
            "total_seconds": summary(streaming, "total_seconds"),
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_example(main)
