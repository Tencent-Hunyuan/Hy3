#!/usr/bin/env python3
"""01 — Basic chat: single-turn and multi-turn."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import MockMessage, MockResponse, dump_json, get_client, get_config, message_to_dict, with_retry


def run_single_turn(client, model: str, mock: bool):
    messages = [{"role": "user", "content": "用一句话介绍你自己。"}]
    print("=== Single-turn request ===")
    print(dump_json({"model": model, "messages": messages, "temperature": 0.9, "top_p": 1.0}))

    if mock:
        resp = MockResponse(MockMessage("你好！我是混元 Hy3，由腾讯混元团队研发的大模型助手。"))
    else:
        resp = with_retry(
            lambda: client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.9,
                top_p=1.0,
                max_tokens=256,
            ),
            label="single-turn",
        )

    msg = resp.choices[0].message
    print("\n=== Response parse ===")
    print(f"finish_reason: {resp.choices[0].finish_reason}")
    print(f"content: {msg.content}")
    if getattr(resp, "usage", None):
        u = resp.usage
        print(f"usage: prompt={u.prompt_tokens} completion={u.completion_tokens} total={u.total_tokens}")
    return msg.content


def run_multi_turn(client, model: str, mock: bool):
    messages = [
        {"role": "system", "content": "你是简洁的编程助手，回答控制在两句话内。"},
        {"role": "user", "content": "Python 怎么读取 JSON 文件？"},
        {
            "role": "assistant",
            "content": "用内置 json 模块：import json; data = json.load(open('a.json'))。",
        },
        {"role": "user", "content": "如果文件很大怎么办？"},
    ]
    print("\n=== Multi-turn request ===")
    print(dump_json({"model": model, "messages": messages}))

    if mock:
        resp = MockResponse(
            MockMessage("大文件可用 ijson 流式解析，或按行读取 NDJSON，避免一次性 load 进内存。")
        )
    else:
        resp = with_retry(
            lambda: client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.9,
                top_p=1.0,
                max_tokens=256,
            ),
            label="multi-turn",
        )

    msg = resp.choices[0].message
    print("\n=== Response parse ===")
    print(dump_json(message_to_dict(msg)))
    return msg.content


def main() -> None:
    cfg = get_config()
    client = get_client(cfg)
    run_single_turn(client, cfg.model, cfg.mock)
    run_multi_turn(client, cfg.model, cfg.mock)


if __name__ == "__main__":
    main()
