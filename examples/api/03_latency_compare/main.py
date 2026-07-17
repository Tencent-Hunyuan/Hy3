#!/usr/bin/env python3
"""03 — Non-streaming vs streaming latency (TTFT / total)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import MockMessage, MockResponse, get_client, get_config, with_retry


PROMPT = "用不超过 80 字说明什么是首 token 时延（TTFT）。"


def measure_non_stream(client, model: str, mock: bool) -> dict:
    messages = [{"role": "user", "content": PROMPT}]
    t0 = time.perf_counter()
    if mock:
        time.sleep(0.15)
        resp = MockResponse(MockMessage("TTFT 是从发出请求到收到第一个输出 token 的时间。"))
        text = resp.choices[0].message.content or ""
    else:
        resp = with_retry(
            lambda: client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.9,
                max_tokens=256,
                stream=False,
            ),
            label="non-stream",
        )
        text = resp.choices[0].message.content or ""
    total_ms = (time.perf_counter() - t0) * 1000
    # Non-stream: first token is only visible when full body arrives ≈ total
    return {
        "mode": "non-stream",
        "ttft_ms": round(total_ms, 1),
        "total_ms": round(total_ms, 1),
        "chars": len(text),
        "preview": text[:80],
    }


def measure_stream(client, model: str, mock: bool) -> dict:
    messages = [{"role": "user", "content": PROMPT}]
    t0 = time.perf_counter()
    ttft_ms = None
    parts: list[str] = []

    if mock:
        for i, piece in enumerate(["TTFT", " 是", " 从发请求", " 到首个", " token", " 的耗时。"]):
            time.sleep(0.03 if i == 0 else 0.01)
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - t0) * 1000
            parts.append(piece)
    else:
        stream = with_retry(
            lambda: client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.9,
                max_tokens=256,
                stream=True,
            ),
            label="stream",
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            piece = chunk.choices[0].delta.content or ""
            if piece:
                if ttft_ms is None:
                    ttft_ms = (time.perf_counter() - t0) * 1000
                parts.append(piece)

    total_ms = (time.perf_counter() - t0) * 1000
    text = "".join(parts)
    return {
        "mode": "stream",
        "ttft_ms": round(ttft_ms or total_ms, 1),
        "total_ms": round(total_ms, 1),
        "chars": len(text),
        "preview": text[:80],
    }


def main() -> None:
    cfg = get_config()
    client = get_client(cfg)

    print("=== Latency compare ===")
    print(f"prompt: {PROMPT}")
    print("definition: TTFT = time until first visible content token; total = until completion\n")

    non_stream = measure_non_stream(client, cfg.model, cfg.mock)
    stream = measure_stream(client, cfg.model, cfg.mock)

    for row in (non_stream, stream):
        print(
            f"[{row['mode']}] ttft_ms={row['ttft_ms']}  total_ms={row['total_ms']}  "
            f"chars={row['chars']}  preview={row['preview']!r}"
        )

    print("\n=== How to read ===")
    print("- Non-stream: client waits for full JSON; TTFT ≈ total.")
    print("- Stream: TTFT is usually much smaller; total may be similar or slightly higher.")
    print("- Numbers vary with network, region, load, and output length.")


if __name__ == "__main__":
    main()
