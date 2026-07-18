#!/usr/bin/env python3
"""02 — Streaming chat with per-chunk parsing."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import get_client, get_config, with_retry


def mock_stream():
    chunks = ["你好", "！", "我是", " Hy3", "，", "很高兴", "为你服务", "。"]
    for i, text in enumerate(chunks):
        time.sleep(0.02)
        yield type(
            "Chunk",
            (),
            {
                "choices": [
                    type(
                        "C",
                        (),
                        {
                            "delta": type("D", (), {"content": text, "role": "assistant" if i == 0 else None})(),
                            "finish_reason": "stop" if i == len(chunks) - 1 else None,
                        },
                    )()
                ],
                "usage": None,
            },
        )()
    # trailing usage chunk
    yield type(
        "Chunk",
        (),
        {
            "choices": [],
            "usage": type("U", (), {"prompt_tokens": 16, "completion_tokens": 12, "total_tokens": 28})(),
        },
    )()


def run_stream(client, model: str, mock: bool) -> str:
    messages = [{"role": "user", "content": "用三句话介绍 Hy3 适合做什么。"}]
    print("=== Streaming request ===")
    print(
        {
            "model": model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
    )

    if mock:
        stream = mock_stream()
    else:
        stream = with_retry(
            lambda: client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.9,
                top_p=1.0,
                max_tokens=512,
                stream=True,
                stream_options={"include_usage": True},
            ),
            label="streaming",
        )

    print("\n=== Chunk parse (delta.content) ===")
    parts: list[str] = []
    finish_reason = None
    usage = None
    n = 0
    for chunk in stream:
        n += 1
        if getattr(chunk, "usage", None):
            usage = chunk.usage
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        delta = choice.delta
        piece = getattr(delta, "content", None) or ""
        if piece:
            parts.append(piece)
            print(piece, end="", flush=True)
        if choice.finish_reason:
            finish_reason = choice.finish_reason
    print("\n")
    print(f"chunks_seen≈{n} finish_reason={finish_reason}")
    if usage:
        print(
            f"usage: prompt={usage.prompt_tokens} "
            f"completion={usage.completion_tokens} total={usage.total_tokens}"
        )
    full = "".join(parts)
    print(f"assembled_content: {full}")
    return full


def main() -> None:
    cfg = get_config()
    client = get_client(cfg)
    run_stream(client, cfg.model, cfg.mock)


if __name__ == "__main__":
    main()
