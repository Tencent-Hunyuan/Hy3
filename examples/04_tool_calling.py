"""Complete a function tool call with the Chat Completions API."""

import json
import os
from typing import Any

from openai import OpenAI


# Chat Completions uses a nested function definition under each tool.
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：深圳",
                    }
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]


def get_weather(city: str) -> dict[str, Any]:
    """Return demo data; replace this with a real business function in production."""
    return {"city": city, "weather": "晴", "temperature": 28}


def main():
    client = OpenAI(
        api_key=os.environ["HY3_API_KEY"],
        base_url=os.getenv(
            "HY3_BASE_URL",
            "https://tokenhub.tencentmaas.com/v1",
        ),
    )
    # Keep the conversation history so tool results can be sent back.
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "深圳今天天气怎么样？"}
    ]

    # A tool workflow may require several model/tool rounds.
    for _ in range(5):
        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        message = response.choices[0].message
        # Preserve the assistant tool-call message in the next request.
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            print(message.content)
            return

        for tool_call in message.tool_calls:
            if tool_call.function.name != "get_weather":
                raise ValueError(f"Unsupported tool: {tool_call.function.name}")

            # Parse the JSON-string arguments and execute the local function.
            arguments = json.loads(tool_call.function.arguments)
            result = get_weather(arguments["city"])
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

    raise RuntimeError("Maximum tool-call rounds exceeded")


if __name__ == "__main__":
    main()
