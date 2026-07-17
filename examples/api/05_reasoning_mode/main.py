#!/usr/bin/env python3
"""05 — Reasoning mode on vs off."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import MockMessage, MockResponse, dump_json, get_client, get_config, message_to_dict, redact, with_retry

QUESTION = "小明有 5 个苹果，给了小红 2 个，又买了 3 个，最后还剩几个？只给最终数字和一句理由。"


def ask(client, model: str, mock: bool, *, thinking_enabled: bool, effort: str | None):
    extra: dict = {}
    if thinking_enabled:
        extra["thinking"] = {"type": "enabled"}
        if effort:
            extra["reasoning_effort"] = effort
    else:
        extra["thinking"] = {"type": "disabled"}

    label = "thinking-on" if thinking_enabled else "thinking-off"
    print(f"\n=== Request ({label}) ===")
    print(dump_json({"model": model, "messages": [{"role": "user", "content": QUESTION}], **extra}))

    if mock:
        if thinking_enabled:
            resp = MockResponse(
                MockMessage(
                    "最终还剩 6 个苹果。",
                    reasoning_content="5-2=3，再 +3 → 6。",
                )
            )
        else:
            resp = MockResponse(MockMessage("6。因为先减 2 再加 3。"))
    else:
        resp = with_retry(
            lambda: client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": QUESTION}],
                temperature=0.9,
                max_tokens=8192 if thinking_enabled else 512,
                extra_body=extra,
            ),
            label=label,
        )

    msg = resp.choices[0].message
    parsed = message_to_dict(msg)
    if "reasoning_content" in parsed:
        parsed["reasoning_content"] = redact(parsed["reasoning_content"], keep=200)
    print(f"=== Response parse ({label}) ===")
    print(dump_json(parsed))
    usage = getattr(resp, "usage", None)
    if usage:
        print(
            f"usage: prompt={usage.prompt_tokens} completion={usage.completion_tokens} "
            f"total={usage.total_tokens}"
        )
    return parsed


def main() -> None:
    cfg = get_config()
    client = get_client(cfg)

    print("Compare thinking disabled vs enabled (reasoning_effort=high).")
    print("Hosted TokenHub uses top-level thinking / reasoning_effort via extra_body.")
    print("Local vLLM uses chat_template_kwargs — see repo README, not this example.")

    off = ask(client, cfg.model, cfg.mock, thinking_enabled=False, effort=None)
    on = ask(client, cfg.model, cfg.mock, thinking_enabled=True, effort="high")

    print("\n=== Diff summary ===")
    print(f"thinking-off has reasoning_content: {'reasoning_content' in off}")
    print(f"thinking-on  has reasoning_content: {'reasoning_content' in on}")
    print(f"thinking-off content: {off.get('content')}")
    print(f"thinking-on  content: {on.get('content')}")


if __name__ == "__main__":
    main()
