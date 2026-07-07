#!/usr/bin/env python3
"""Hy3 tool calling example with a deterministic local weather tool.

Environment:
  HY3_BASE_URL=http://127.0.0.1:8000/v1
  HY3_API_KEY=EMPTY
  HY3_MODEL=hy3

Run:
  python3 examples/api/tool_calling.py

Sample output:
  parsed_tool_call: get_weather({"city": "Shenzhen"})
  tool_result: {"city": "Shenzhen", "temperature_c": 29, ...}
  final_content: It is rainy in Shenzhen, so bring an umbrella.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from common import (
    MODEL,
    make_client,
    print_json,
    print_runtime_config,
    request_options,
    to_plain,
)

MAX_TOOL_ROUNDS = int(os.getenv("HY3_MAX_TOOL_ROUNDS", "4"))


WEATHER_BY_CITY = {
    "Shenzhen": {
        "city": "Shenzhen",
        "condition": "light rain",
        "temperature_c": 29,
        "humidity_percent": 82,
        "umbrella_recommended": True,
    },
    "Beijing": {
        "city": "Beijing",
        "condition": "clear",
        "temperature_c": 24,
        "humidity_percent": 40,
        "umbrella_recommended": False,
    },
}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a supported city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, for example Shenzhen or Beijing.",
                    }
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]


def get_weather(city: str) -> dict[str, Any]:
    return WEATHER_BY_CITY.get(
        city,
        {
            "city": city,
            "condition": "unknown",
            "error": "City is not in the local example data.",
        },
    )


def parse_arguments(arguments: Optional[str]) -> dict[str, Any]:
    if not arguments:
        return {}
    try:
        return json.loads(arguments)
    except json.JSONDecodeError as exc:
        return {"_parse_error": str(exc), "_raw_arguments": arguments}


def assistant_message_to_dict(message: Any) -> dict[str, Any]:
    tool_calls = getattr(message, "tool_calls", None) or []
    payload: dict[str, Any] = {
        "role": "assistant",
        "content": message.content,
    }
    if tool_calls:
        payload["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": tool_call.type,
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in tool_calls
        ]
    return payload


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if "_parse_error" in arguments:
        return {"error": "Invalid JSON arguments", "details": arguments}
    if name == "get_weather":
        return get_weather(city=str(arguments.get("city", "")))
    return {"error": f"Unknown tool: {name}"}


def print_response(response: Any) -> Any:
    choice = response.choices[0]
    message = choice.message
    print("\n=== assistant response ===")
    print("id:", response.id)
    print("model:", response.model)
    print("finish_reason:", choice.finish_reason)
    print("content:", message.content)
    if getattr(message, "tool_calls", None):
        print_json("tool_calls", message.tool_calls)
    if response.usage:
        print_json("usage", response.usage)
    return message


def main() -> None:
    print_runtime_config()
    client = make_client()
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                "Use the weather tool to check Shenzhen. "
                "Then tell me if I should bring an umbrella."
            ),
        }
    ]

    for round_index in range(1, MAX_TOOL_ROUNDS + 1):
        request = {
            "model": MODEL,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "temperature": 0.2,
            "top_p": 1.0,
            "max_tokens": 512,
            **request_options(reasoning_effort="no_think"),
        }
        print_json(f"tool round {round_index} request", request)
        response = client.chat.completions.create(**request)
        message = print_response(response)
        tool_calls = getattr(message, "tool_calls", None) or []

        if not tool_calls:
            print("\n=== final_content ===")
            print(message.content)
            return

        messages.append(assistant_message_to_dict(message))

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = parse_arguments(tool_call.function.arguments)
            result = execute_tool(function_name, arguments)

            print("\n=== parsed_tool_call ===")
            print(f"{function_name}({json.dumps(arguments, ensure_ascii=False)})")
            print_json("tool_result", result)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError(f"Tool loop exceeded {MAX_TOOL_ROUNDS} rounds")


if __name__ == "__main__":
    main()
