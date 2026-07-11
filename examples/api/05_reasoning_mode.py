"""比较 Hy3 的无思考与高强度推理模式。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Literal

from common import (
    Hy3Config,
    create_client,
    print_json,
    reasoning_extra_body,
    summarize_completion,
)


QUESTION = "A train travels 120 km in 2 hours. What is its average speed?"


@dataclass(frozen=True)
class ModeResult:
    effort: Literal["no_think", "high"]
    reasoning: str
    reasoning_details: list[Any]
    content: str
    elapsed: float
    usage: dict[str, Any] | None


def run_mode(
    client: Any,
    config: Hy3Config,
    effort: Literal["no_think", "high"],
    question: str,
    *,
    clock: Callable[[], float] = time.perf_counter,
) -> ModeResult:
    """使用指定推理强度执行同一个问题并记录耗时。"""
    if effort not in ("no_think", "high"):
        raise ValueError("effort must be no_think or high")

    started = clock()
    completion = client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": question}],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        extra_body=reasoning_extra_body(config, effort),
    )
    summary = summarize_completion(completion)
    elapsed = clock() - started
    return ModeResult(
        effort=effort,
        reasoning=summary["reasoning"],
        reasoning_details=summary["reasoning_details"],
        content=summary["content"] or "",
        elapsed=elapsed,
        usage=summary["usage"],
    )


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    for effort in ("no_think", "high"):
        result = run_mode(client, config, effort, QUESTION)
        print_json(f"Reasoning mode: {effort}", result)
        if not result.reasoning and not result.reasoning_details:
            print("Reasoning unavailable: backend did not expose reasoning text.")


if __name__ == "__main__":
    main()
