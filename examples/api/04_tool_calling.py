"""Hy3 single tool-call parsing and bounded multi-round tool loop."""

from __future__ import annotations

import argparse
import json
from typing import Any, Callable

from common import (
    assistant_message_dict,
    create_client,
    load_config,
    usage_dict,
)

WEATHER_DATA = {
    "北京": {"temperature_c": 28, "condition": "晴", "humidity": 42},
    "上海": {"temperature_c": 31, "condition": "多云", "humidity": 67},
    "深圳": {"temperature_c": 30, "condition": "阵雨", "humidity": 79},
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询示例数据集中指定中国城市的天气。",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "城市名称"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]


def get_weather(city: str) -> dict[str, Any]:
    """Return deterministic local data; this example calls no weather API."""

    if not isinstance(city, str) or not city.strip():
        raise ValueError("city must be a non-empty string")
    city = city.strip()
    if city not in WEATHER_DATA:
        return {"city": city, "error": "示例数据中没有该城市"}
    return {"city": city, **WEATHER_DATA[city]}


TOOL_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {"get_weather": get_weather}


def execute_tool_call(tool_call: Any) -> str:
    """Validate and execute one allow-listed tool call."""

    name = tool_call.function.name
    if name not in TOOL_HANDLERS:
        return json.dumps({"error": f"unknown tool: {name}"}, ensure_ascii=False)
    try:
        arguments = json.loads(tool_call.function.arguments or "{}")
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be a JSON object")
        result = TOOL_HANDLERS[name](**arguments)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        result = {"error": str(exc)}
    return json.dumps(result, ensure_ascii=False)


def run_tool_loop(
    client: Any,
    model: str,
    messages: list[dict[str, Any]],
    *,
    max_rounds: int = 5,
    single_round: bool = False,
) -> str | None:
    """Run tool calls until the model returns text or the round limit is reached."""

    for round_number in range(1, max_rounds + 1):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice=(
                {"type": "function", "function": {"name": "get_weather"}}
                if single_round
                else ("required" if round_number == 1 else "auto")
            ),
            parallel_tool_calls=True,
            temperature=0.2,
            max_tokens=1024,
            extra_body={"thinking": {"type": "disabled"}},
        )
        if not response.choices:
            raise RuntimeError("The API returned no choices")
        choice = response.choices[0]
        message = choice.message
        print(
            f"round {round_number}: id={response.id}, model={response.model}, "
            f"finish_reason={choice.finish_reason}, "
            f"usage={usage_dict(response)}"
        )

        tool_calls = message.tool_calls or []
        if not tool_calls:
            print("assistant:", message.content)
            return message.content

        messages.append(assistant_message_dict(message))
        for tool_call in tool_calls:
            result = execute_tool_call(tool_call)
            print(
                "tool request:",
                tool_call.function.name,
                tool_call.function.arguments,
            )
            print("tool result:", result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

        if single_round:
            print("single-round mode: tool calls parsed and executed; stopping here")
            return None

    raise RuntimeError(f"Tool loop exceeded {max_rounds} rounds")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--single",
        action="store_true",
        help="force, parse, and execute exactly one round of tool calls",
    )
    args = parser.parse_args()

    config = load_config()
    client = create_client(config)
    messages = [
        {
            "role": "user",
            "content": "请查询北京和上海的天气，并告诉我哪个城市更暖和。",
        }
    ]
    run_tool_loop(client, config.model, messages, single_round=args.single)


if __name__ == "__main__":
    main()
