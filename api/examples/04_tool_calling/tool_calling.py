"""Run a complete multi-round Hy3 tool-calling loop."""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import create_client, model_name, print_response  # noqa: E402

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]


def get_weather(city: str) -> dict[str, Any]:
    """Demo tool. Replace this deterministic data with a real weather API."""
    return {"city": city, "temperature_c": 26, "condition": "晴"}


def execute_tool(name: str, arguments: str) -> str:
    if name != "get_weather":
        return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
    try:
        values = json.loads(arguments)
        return json.dumps(get_weather(city=values["city"]), ensure_ascii=False)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        return json.dumps({"error": f"invalid arguments: {exc}"}, ensure_ascii=False)


def main() -> None:
    client = create_client()
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "深圳今天天气如何？适合穿什么？"}
    ]

    for round_number in range(1, 6):
        print(f"=== Model round {round_number} ===")
        response = client.chat.completions.create(
            model=model_name(), messages=messages, tools=TOOLS, tool_choice="auto"
        )
        print_response(response)
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            return
        for call in message.tool_calls:
            result = execute_tool(call.function.name, call.function.arguments)
            print(f"tool result ({call.id}): {result}")
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

    raise RuntimeError("tool loop exceeded 5 model rounds")


if __name__ == "__main__":
    main()
