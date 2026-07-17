"""Run one safe tool request through a bounded multi-round Hy3 tool loop."""

from __future__ import annotations

from typing import Any

from common import (
    ApiConfig,
    create_chat_completion,
    create_client,
    get_field,
    print_response,
    run_example,
    run_tool_loop,
    thinking_body,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "convert_temperature",
            "description": "Convert a temperature between Celsius and Fahrenheit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "from_unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    "to_unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["value", "from_unit", "to_unit"],
                "additionalProperties": False,
            },
        },
    }
]


def convert_temperature(value: float, from_unit: str, to_unit: str) -> dict[str, Any]:
    if from_unit == to_unit:
        converted = value
    elif from_unit == "fahrenheit":
        converted = (value - 32) * 5 / 9
    else:
        converted = value * 9 / 5 + 32
    return {
        "input": {"value": value, "unit": from_unit},
        "output": {"value": round(converted, 4), "unit": to_unit},
    }


def main() -> None:
    config = ApiConfig.from_env()
    client = create_client(config)

    def show_round(round_index: int, response: Any) -> None:
        choice = get_field(response, "choices", [None])[0]
        print(
            f"\n=== Model response {round_index + 1}: {get_field(choice, 'finish_reason')} ==="
        )
        print_response(response, secrets=[config.api_key])

    result = run_tool_loop(
        lambda **request: create_chat_completion(client, **request),
        messages=[
            {
                "role": "user",
                "content": "把 68 华氏度转换为摄氏度，并简洁说明结果。",
            }
        ],
        tools=TOOLS,
        handlers={"convert_temperature": convert_temperature},
        request_kwargs={
            "model": config.model,
            "temperature": 0,
            "max_tokens": 2048,
            "tool_choice": "auto",
            "extra_body": thinking_body(True, "medium"),
        },
        max_tool_rounds=4,
        on_response=show_round,
    )
    print(f"\nCompleted after {result.tool_rounds} tool round(s).")


if __name__ == "__main__":
    run_example(main)
