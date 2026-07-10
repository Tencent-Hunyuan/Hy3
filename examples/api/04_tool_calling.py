from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from common import (
    Hy3Config,
    assistant_message_to_dict,
    create_client,
    object_to_dict,
    print_json,
    reasoning_extra_body,
    summarize_completion,
)


DEMO_WEATHER = {
    "Beijing": {"condition": "sunny", "temperature_c": 24},
    "Shenzhen": {"condition": "rainy", "temperature_c": 29},
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Return deterministic demo weather data for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name: Beijing or Shenzhen.",
                    }
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]


def tool_error(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}


def execute_tool_call(tool_call: Any) -> dict[str, Any]:
    call = object_to_dict(tool_call)
    if not isinstance(call, dict):
        return tool_error("invalid_arguments", "tool call must be an object")
    function = call.get("function")
    if not isinstance(function, dict):
        return tool_error("invalid_arguments", "tool function must be an object")
    name = function.get("name")
    if name != "get_weather":
        return tool_error("unknown_tool", f"unsupported tool: {name}")
    raw_arguments = function.get("arguments")
    if not isinstance(raw_arguments, str):
        return tool_error("invalid_arguments", "tool arguments must be a string")
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return tool_error("invalid_arguments", "arguments must be valid JSON")
    if not isinstance(arguments, dict):
        return tool_error(
            "invalid_arguments",
            "tool arguments must decode to an object",
        )
    city_value = arguments.get("city")
    if not isinstance(city_value, str) or not city_value.strip():
        return tool_error("missing_argument", "city is required")
    city = city_value.strip()
    weather = DEMO_WEATHER.get(city)
    if weather is None:
        return tool_error("city_not_found", f"no demo data for {city}")
    return {"ok": True, "city": city, **weather, "source": "demo data"}


def run_tool_loop(
    client: Any,
    config: Hy3Config,
    messages: list[dict[str, Any]],
    *,
    max_rounds: int = 4,
) -> dict[str, Any]:
    for _round_number in range(1, max_rounds + 1):
        response = client.chat.completions.create(
            model=config.model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.9,
            top_p=1.0,
            max_tokens=512,
            extra_body=reasoning_extra_body(config, "no_think"),
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise RuntimeError("tool completion did not contain any choices")
        message = getattr(choices[0], "message", None)
        if message is None:
            raise RuntimeError("tool completion did not contain a message")
        raw_tool_calls = getattr(message, "tool_calls", None)
        if isinstance(raw_tool_calls, (str, bytes, Mapping)):
            raise RuntimeError("tool completion returned invalid tool_calls")
        if raw_tool_calls is None:
            tool_calls = []
        else:
            try:
                tool_calls = list(raw_tool_calls)
            except TypeError:
                raise RuntimeError(
                    "tool completion returned invalid tool_calls"
                ) from None
        if not tool_calls:
            return summarize_completion(response)

        normalized_tool_calls = []
        for tool_call in tool_calls:
            normalized = object_to_dict(tool_call)
            if not isinstance(normalized, dict):
                raise RuntimeError(
                    "tool completion returned an invalid tool call"
                )
            call_id = normalized.get("id")
            function = normalized.get("function")
            if (
                not isinstance(call_id, str)
                or not call_id.strip()
                or not isinstance(function, dict)
            ):
                raise RuntimeError(
                    "tool completion returned an invalid tool call"
                )
            normalized_tool_calls.append(normalized)

        assistant_message = assistant_message_to_dict(message)
        assistant_message["tool_calls"] = normalized_tool_calls
        messages.append(assistant_message)
        for tool_call in normalized_tool_calls:
            result = execute_tool_call(tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    raise RuntimeError(f"tool loop exceeded max_rounds={max_rounds}")


def main() -> None:
    config = Hy3Config.from_env()
    messages = [
        {
            "role": "user",
            "content": "Use the weather tool for Shenzhen, then answer briefly.",
        }
    ]
    result = run_tool_loop(create_client(config), config, messages)
    print_json("Tool loop result", result)


if __name__ == "__main__":
    main()
