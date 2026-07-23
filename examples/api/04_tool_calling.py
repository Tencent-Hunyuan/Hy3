"""Hy3 API example 04: execute tool calls in a bounded conversation loop."""

from __future__ import annotations

import json
from typing import Any

from hy3_client import Hy3Config, create_client, reasoning_options

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "convert_temperature",
            "description": "Convert a temperature between Celsius and Fahrenheit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number", "description": "Temperature to convert."},
                    "to_unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Target unit.",
                    },
                },
                "required": ["value", "to_unit"],
                "additionalProperties": False,
            },
        },
    }
]


def convert_temperature(value: float, to_unit: str) -> dict[str, float | str]:
    if to_unit == "fahrenheit":
        converted = value * 9 / 5 + 32
        symbol = "°F"
    elif to_unit == "celsius":
        converted = (value - 32) * 5 / 9
        symbol = "°C"
    else:
        raise ValueError(f"unsupported target unit: {to_unit}")
    return {"value": round(converted, 2), "unit": symbol}


def execute_tool_call(tool_call: Any) -> str:
    if tool_call.function.name != "convert_temperature":
        return json.dumps({"error": "unknown tool"})
    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
        result = convert_temperature(**arguments)
        return json.dumps(result)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return json.dumps({"error": str(error)})


def assistant_history_message(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    return {
        "role": "assistant",
        "content": message.content,
        "tool_calls": message.tool_calls,
    }


def run_tool_loop(client: Any, config: Hy3Config, max_rounds: int = 4) -> str:
    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": "Convert 21 degrees Celsius to Fahrenheit, then explain the result.",
        }
    ]
    for round_number in range(1, max_rounds + 1):
        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.0,
            max_tokens=512,
            extra_body=reasoning_options("no_think"),
        )
        message = response.choices[0].message
        if not message.tool_calls:
            return message.content or ""

        print(f"Round {round_number}: model requested {len(message.tool_calls)} tool call(s)")
        messages.append(assistant_history_message(message))
        for tool_call in message.tool_calls:
            result = execute_tool_call(tool_call)
            print(f"  {tool_call.function.name}({tool_call.function.arguments}) -> {result}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )
    raise RuntimeError(f"tool loop exceeded {max_rounds} rounds")


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    print(f"Connecting with {config.safe_summary()}")
    print("Assistant: " + run_tool_loop(client, config))


if __name__ == "__main__":
    main()
