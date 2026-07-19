"""Hy3 Example 02: Streaming request + per-chunk parsing.

Demonstrates streaming mode via the OpenAI-compatible API, printing tokens
incrementally and assembling the full text at the end.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import (  # noqa: E402
    chat_completion,
    get_config,
    iter_stream_text,
    make_client,
)


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    messages = [
        {
            "role": "user",
            "content": (
                "请用中文写一段关于「秋天的银杏林」的短文，包含颜色、声音和心情的描写，至少三句话。"
            ),
        },
    ]

    print("=== Streaming Output (per-chunk print) ===")
    stream = chat_completion(client, messages, reasoning="no_think", stream=True)

    full_text_parts = []
    for content in iter_stream_text(stream):
        print(content, end="", flush=True)
        full_text_parts.append(content)

    print("\n\n=== Stream ended, assembling full text ===")
    full_text = "".join(full_text_parts)
    print(full_text)


if __name__ == "__main__":
    main()
