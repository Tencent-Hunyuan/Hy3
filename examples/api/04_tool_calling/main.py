#!/usr/bin/env python3
"""04 — Tool calling: one-shot + multi-turn tool loop."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import (
    MockMessage,
    MockResponse,
    MockToolCall,
    dump_json,
    get_client,
    get_config,
    message_to_dict,
    with_retry,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 深圳"},
                },
                "required": ["city"],
            },
        },
    }
]


def get_weather(city: str) -> str:
    # Demo stub — replace with real API in production.
    catalog = {
        "深圳": "多云，气温 24~30°C，湿度 70%",
        "北京": "晴，气温 18~28°C，湿度 35%",
    }
    return catalog.get(city, f"{city}：暂无数据（demo stub）")


def run_one_shot(client, model: str, mock: bool):
    messages = [{"role": "user", "content": "深圳今天天气怎么样？"}]
    print("=== One-shot tool call request ===")
    print(dump_json({"model": model, "messages": messages, "tools": TOOLS, "tool_choice": "auto"}))

    if mock:
        resp = MockResponse(
            MockMessage(
                "我来查一下深圳天气。",
                tool_calls=[MockToolCall("get_weather", '{"city":"深圳"}')],
            ),
            finish_reason="tool_calls",
        )
    else:
        resp = with_retry(
            lambda: client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.9,
            ),
            label="tool-one-shot",
        )

    msg = resp.choices[0].message
    print("\n=== Response parse ===")
    print(f"finish_reason: {resp.choices[0].finish_reason}")
    print(dump_json(message_to_dict(msg)))
    return messages, msg


def run_tool_loop(client, model: str, mock: bool, messages, first_msg) -> str:
    """Append assistant + tool results, then ask model for the final answer."""
    messages = list(messages)
    messages.append(message_to_dict(first_msg))

    for tc in first_msg.tool_calls or []:
        args = json.loads(tc.function.arguments)
        result = get_weather(**args) if tc.function.name == "get_weather" else "unknown tool"
        tool_msg = {
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        }
        messages.append(tool_msg)
        print("\n=== Tool executed ===")
        print(dump_json(tool_msg))

    print("\n=== Follow-up request (with tool results) ===")
    print(dump_json({"model": model, "messages": messages, "tools": TOOLS}))

    if mock:
        resp = MockResponse(
            MockMessage(
                "根据查询，深圳今天多云，气温 24~30°C，湿度 70%。出门可适当防晒。",
                reasoning_content="已拿到 get_weather 结果，整理成对用户友好的中文回复。",
            )
        )
    else:
        resp = with_retry(
            lambda: client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.9,
                extra_body={"reasoning_effort": "high"},
            ),
            label="tool-followup",
        )

    final = resp.choices[0].message
    print("\n=== Final response parse ===")
    print(dump_json(message_to_dict(final)))
    return final.content or ""


def main() -> None:
    cfg = get_config()
    client = get_client(cfg)
    messages, first = run_one_shot(client, cfg.model, cfg.mock)
    if not first.tool_calls:
        print("Model answered without tools:", first.content)
        return
    run_tool_loop(client, cfg.model, cfg.mock, messages, first)


if __name__ == "__main__":
    main()
