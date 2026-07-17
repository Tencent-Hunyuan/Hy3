"""Compare documented Hy3 thinking off/low/medium/high modes."""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any

from common import (
    ApiConfig,
    create_chat_completion,
    create_client,
    get_field,
    run_example,
    thinking_body,
)

DOCUMENTED_MODES = ("off", "low", "medium", "high")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=DOCUMENTED_MODES,
        default=list(DOCUMENTED_MODES),
        help="modes to run (default: all documented modes)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ApiConfig.from_env()
    client = create_client(config)
    try:
        max_tokens = int(os.environ.get("HY3_REASONING_MAX_TOKENS", "4096"))
    except ValueError as exc:
        raise SystemExit("HY3_REASONING_MAX_TOKENS must be an integer") from exc
    if max_tokens < 1:
        raise SystemExit("HY3_REASONING_MAX_TOKENS must be positive")

    results: list[dict[str, Any]] = []
    for mode in args.modes:
        body = thinking_body(False) if mode == "off" else thinking_body(True, mode)
        started = time.perf_counter()
        response = create_chat_completion(
            client,
            model=config.model,
            messages=[
                {
                    "role": "user",
                    "content": "有三个盒子标签都贴错了，怎样只取一次球确定每个盒子的内容？",
                }
            ],
            temperature=0,
            max_tokens=max_tokens,
            extra_body=body,
        )
        elapsed = time.perf_counter() - started
        choice = response.choices[0]
        message = choice.message
        reasoning = get_field(message, "reasoning_content") or ""
        usage = get_field(response, "usage")
        results.append(
            {
                "mode": mode,
                "elapsed_seconds": elapsed,
                "finish_reason": choice.finish_reason,
                "reasoning_content": reasoning,
                "answer": message.content,
                "usage": {
                    "prompt_tokens": get_field(usage, "prompt_tokens"),
                    "completion_tokens": get_field(usage, "completion_tokens"),
                    "total_tokens": get_field(usage, "total_tokens"),
                },
            }
        )

    report = {
        "model": config.model,
        "note": "Single samples illustrate fields and cost/latency; they do not prove quality.",
        "results": results,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_example(main)
