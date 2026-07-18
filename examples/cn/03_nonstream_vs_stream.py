"""Hy3 Example 03: Non-streaming vs streaming latency comparison.

Measures:
  - Non-streaming: total latency
  - Streaming: Time To First Token (TTFT) and total latency
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import chat_completion, collect_stream, get_config, make_client  # noqa: E402


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    messages = [
        {
            "role": "user",
            "content": (
                "请用中文简要介绍混合专家模型（MoE）的工作原理，"
                "并举一个生活中的类比，回答约 150 字。"
            ),
        },
    ]

    # ---------- Non-streaming ----------
    print("=== Non-streaming call ===")
    t0 = time.perf_counter()
    response = chat_completion(client, messages, reasoning="no_think", stream=False)
    nonstream_total = time.perf_counter() - t0
    nonstream_text = response.choices[0].message.content
    print(f"Response content:\n{nonstream_text}")
    print(f"\nNon-streaming total latency: {nonstream_total:.3f} s\n")

    # ---------- Streaming ----------
    print("=== Streaming call ===")
    stream = chat_completion(client, messages, reasoning="no_think", stream=True)
    stream_text, ttft, stream_total = collect_stream(stream)
    print(f"Response content:\n{stream_text}")
    ttft_str = f"{ttft:.3f} s" if ttft is not None else "N/A"
    print(f"\nStreaming TTFT (Time To First Token): {ttft_str}")
    print(f"Streaming total latency: {stream_total:.3f} s\n")

    # ---------- Comparison summary ----------
    print("=== Comparison summary ===")
    print(f"Non-streaming total latency:           {nonstream_total:.3f} s")
    print(f"Streaming  TTFT:                       {ttft_str}")
    print(f"Streaming  total latency:              {stream_total:.3f} s")
    if ttft is not None and nonstream_total > 0:
        print(f"TTFT / Non-streaming total latency:    {ttft / nonstream_total:.1%}")
        print(
            "Tip: streaming lets UIs start rendering earlier even when total "
            "generation time is similar."
        )


if __name__ == "__main__":
    main()
