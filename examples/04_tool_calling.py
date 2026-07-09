import json
import os
from typing import Any

from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def get_weather(city: str) -> str:
    data = {
        "Beijing": "Sunny, 28C",
        "Shenzhen": "Cloudy, 30C",
        "Shanghai": "Light rain, 27C",
    }
    return data.get(city, "Weather data is unavailable for this city.")


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get mock weather information for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, for example Beijing or Shenzhen.",
                    }
                },
                "required": ["city"],
            },
        },
    }
]


def run_tool_call(tool_call: Any) -> str:
    name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments or "{}")

    if name == "get_weather":
        return get_weather(**arguments)
    return f"Unknown tool: {name}"


def main() -> None:
    messages = [
        {
            "role": "user",
            "content": "What is the weather in Beijing? Use the available tool.",
        }
    ]

    for _ in range(3):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=256,
        )
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            print(message.content)
            return

        for tool_call in message.tool_calls:
            result = run_tool_call(tool_call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    raise RuntimeError("Tool calling did not finish within the maximum number of rounds.")


if __name__ == "__main__":
    main()
