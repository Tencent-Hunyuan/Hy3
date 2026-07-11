import json
import os
from typing import Any

from openai import OpenAI


base_url = os.getenv(
    "HY3_BASE_URL",
    "http://127.0.0.1:8000/v1",
)

api_key = os.getenv(
    "HY3_API_KEY",
    "EMPTY",
)

model = os.getenv(
    "HY3_MODEL",
    "hy3",
)


client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)


def get_weather(city: str) -> dict[str, Any]:
    """Return mock weather data for demonstration."""

    mock_weather = {
        "Tokyo": {
            "temperature_c": 28,
            "condition": "Sunny",
        },
        "Shanghai": {
            "temperature_c": 31,
            "condition": "Cloudy",
        },
        "Beijing": {
            "temperature_c": 30,
            "condition": "Clear",
        },
    }

    weather = mock_weather.get(
        city,
        {
            "temperature_c": 25,
            "condition": "Unknown",
        },
    )

    return {
        "city": city,
        **weather,
    }


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get mock weather data for a city "
                "for tool-calling demonstration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": (
                            "City name, for example Tokyo."
                        ),
                    }
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]


def print_json(
    title: str,
    data: Any,
) -> None:
    """Print JSON-compatible data."""

    print(f"\n=== {title} ===")

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )


def run_single_tool_call() -> None:
    """Ask Hy3 to select a tool and inspect the tool call."""

    print("\n\n############################")
    print("# Single tool call")
    print("############################")

    messages = [
        {
            "role": "user",
            "content": (
                "What is the weather in Tokyo? "
                "Use the available tool."
            ),
        }
    ]

    request_payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": 0.9,
        "top_p": 1.0,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": "no_think"
            }
        },
    }

    print_json(
        "Complete request",
        request_payload,
    )

    response = client.chat.completions.create(
        **request_payload
    )

    print("\n=== Complete response ===")
    print(response.model_dump_json(indent=2))

    message = response.choices[0].message

    if not message.tool_calls:
        print("\nNo tool call was returned.")
        print(
            "Assistant content:",
            message.content,
        )
        return

    print("\n=== Parsed tool calls ===")

    for tool_call in message.tool_calls:
        print(f"Tool call ID: {tool_call.id}")
        print(
            "Function name:",
            tool_call.function.name,
        )
        print(
            "Raw arguments:",
            tool_call.function.arguments,
        )

        arguments = json.loads(
            tool_call.function.arguments
        )

        print(
            "Parsed arguments:",
            arguments,
        )


def run_tool_loop() -> None:
    """Execute a tool locally and send its result back to Hy3."""

    print("\n\n############################")
    print("# Multi-turn tool loop")
    print("############################")

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                "What is the weather in Tokyo? "
                "Use the available tool and give me "
                "a short final answer."
            ),
        }
    ]

    first_request = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": 0.9,
        "top_p": 1.0,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": "no_think"
            }
        },
    }

    print_json(
        "First request",
        first_request,
    )

    first_response = client.chat.completions.create(
        **first_request
    )

    print("\n=== First complete response ===")
    print(
        first_response.model_dump_json(
            indent=2
        )
    )

    assistant_message = (
        first_response
        .choices[0]
        .message
    )

    if not assistant_message.tool_calls:
        print("\nNo tool call was returned.")
        print(
            "Assistant content:",
            assistant_message.content,
        )
        return

    # Preserve the assistant tool-call message.
    messages.append(
        assistant_message.model_dump(
            exclude_none=True
        )
    )

    for tool_call in assistant_message.tool_calls:
        function_name = tool_call.function.name

        arguments = json.loads(
            tool_call.function.arguments
        )

        print("\n=== Executing local tool ===")
        print(f"Function: {function_name}")
        print(f"Arguments: {arguments}")

        if function_name == "get_weather":
            tool_result = get_weather(
                city=arguments["city"]
            )
        else:
            tool_result = {
                "error": (
                    f"Unknown tool: {function_name}"
                )
            }

        print_json(
            "Tool result",
            tool_result,
        )

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    tool_result,
                    ensure_ascii=False,
                ),
            }
        )

    second_request = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "temperature": 0.9,
        "top_p": 1.0,
        "extra_body": {
            "chat_template_kwargs": {
                "reasoning_effort": "no_think"
            }
        },
    }

    print_json(
        "Second request",
        second_request,
    )

    final_response = client.chat.completions.create(
        **second_request
    )

    print("\n=== Final complete response ===")
    print(
        final_response.model_dump_json(
            indent=2
        )
    )

    final_message = (
        final_response
        .choices[0]
        .message
    )

    print("\n=== Final parsed answer ===")
    print(final_message.content)


if __name__ == "__main__":
    run_single_tool_call()
    run_tool_loop()
