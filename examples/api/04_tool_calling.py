from __future__ import annotations

import json
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
    function = call.get("function") or {}
    name = function.get("name")
    try:
        arguments = json.loads(function.get("arguments") or "{}")
    except json.JSONDecodeError:
        return tool_error("invalid_arguments", "arguments must be valid JSON")
    if name != "get_weather":
        return tool_error("unknown_tool", f"unsupported tool: {name}")
    if not isinstance(arguments, dict) or not arguments.get("city"):
        return tool_error("missing_argument", "city is required")
    city = str(arguments["city"])
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
        message = response.choices[0].message
        tool_calls = list(message.tool_calls or [])
        if not tool_calls:
            return summarize_completion(response)

        messages.append(assistant_message_to_dict(message))
        for tool_call in tool_calls:
            result = execute_tool_call(tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
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
