"""Complete a function tool call with the Responses API."""

import json
import os
from typing import Any

from openai import OpenAI


# Responses API uses a flat function tool definition.
TOOLS = [
    {
        "type": "function",
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
    }
]


def get_weather(city: str) -> dict[str, Any]:
    """Return demo data; replace this with a real business function in production."""
    return {"city": city, "weather": "晴", "temperature": 28}


def main() -> None:
    client = OpenAI(
        api_key=os.environ["HY3_API_KEY"],
        base_url=os.getenv(
            "HY3_BASE_URL",
            "https://tokenhub.tencentmaas.com/v1",
        ),
    )
    user_input = "深圳今天天气怎么样？"

    # First request: let the model decide whether to call the tool.
    response = client.responses.create(
        model="hy3",
        input=user_input,
        tools=TOOLS,
        tool_choice="auto",
    )

    input_items: list[dict[str, Any]] = [
        {"role": "user", "content": user_input}
    ]
    has_tool_call = False

    # Inspect output Items for function_call entries.
    for item in response.output:
        item_data = item.model_dump(exclude_none=True)
        input_items.append(item_data)

        if item_data.get("type") != "function_call":
            continue

        has_tool_call = True
        if item_data["name"] != "get_weather":
            raise ValueError(f"Unsupported tool: {item_data['name']}")

        # The arguments field is a JSON string and must be parsed first.
        arguments = json.loads(item_data["arguments"])
        result = get_weather(arguments["city"])
        input_items.append(
            {
                "type": "function_call_output",
                "call_id": item_data["call_id"],
                "output": json.dumps(result, ensure_ascii=False),
            }
        )

    # Send the function_call_output back to obtain the final answer.
    if has_tool_call:
        response = client.responses.create(
            model="hy3",
            input=input_items,
            tools=TOOLS,
            tool_choice="auto",
        )

    print(response.output_text)


if __name__ == "__main__":
    main()
