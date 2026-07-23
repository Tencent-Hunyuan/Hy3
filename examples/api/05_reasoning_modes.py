"""Hy3 API example 05: compare no_think, low, and high reasoning modes."""

from __future__ import annotations

import os
import time
from typing import Any

from hy3_client import Hy3Config, create_client, reasoning_options, split_message

PROMPT = (
    "A service has 99.9% availability. Assuming independent downtime, what is the "
    "probability that two redundant instances are both unavailable? Explain briefly."
)


def run_mode(client: Any, config: Hy3Config, effort: str) -> None:
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.0,
        top_p=1.0,
        max_tokens=2048 if effort == "high" else 768,
        extra_body=reasoning_options(effort),
    )
    elapsed = time.perf_counter() - started
    reasoning, content = split_message(response.choices[0].message)

    print(f"\n=== reasoning_effort={effort} ===")
    print(f"Elapsed: {elapsed:.3f}s")
    print(f"Reasoning characters returned: {len(reasoning)}")
    if os.getenv("HY3_SHOW_REASONING", "0") == "1" and reasoning:
        print("Reasoning:\n" + reasoning)
    print("Final answer:\n" + content)


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    print(f"Connecting with {config.safe_summary()}")
    for effort in ("no_think", "low", "high"):
        run_mode(client, config, effort)


if __name__ == "__main__":
    main()
