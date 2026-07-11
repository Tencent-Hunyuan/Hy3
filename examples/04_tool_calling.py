"""
04_tool_calling.py

展示内容：
1. tools 参数怎么传
2. 模型返回 tool_calls 后如何解析
3. 本地执行工具后，如何把结果追加回 messages
4. 多轮工具循环直到得到最终回答

运行方式：
    pip install openai
    python examples/04_tool_calling.py

示例输出：
    Tool requested: get_weather({"city": "Shanghai"})
    Tool result: {"city": "Shanghai", "temperature": "25°C", "condition": "sunny"}
    Final answer:
    上海当前天气晴朗，气温 25°C...
"""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")


def get_weather(city: str) -> dict[str, str]:
    return {"city": city, "temperature": "25°C", "condition": "sunny"}


def calculator(expression: str) -> dict[str, Any]:
    allowed = {"abs": abs, "round": round}
    value = eval(expression, {"__builtins__": {}}, allowed)
    return {"expression": expression, "result": value}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get mock weather data for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a simple math expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression such as 25 * 1.8 + 32",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "get_weather":
        return get_weather(arguments["city"])
    if name == "calculator":
        return calculator(arguments["expression"])
    raise ValueError(f"Unknown tool: {name}")


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    messages: list[dict[str, Any]] = [
        {
            "role": "user",
            "content": "请告诉我上海的天气，并把 25°C 转换成华氏度。",
        }
    ]

    for round_index in range(4):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            temperature=0.2,
            top_p=1.0,
            max_tokens=512,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "low"}},
        )

        message = response.choices[0].message
        tool_calls = message.tool_calls or []

        if not tool_calls:
            print("Final answer:")
            print(message.content or "")
            break

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [],
        }
        tool_messages: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments or "{}")
            print(
                f"Tool requested: {function_name}({json.dumps(arguments, ensure_ascii=False)})"
            )

            tool_result = execute_tool(function_name, arguments)
            print(f"Tool result: {json.dumps(tool_result, ensure_ascii=False)}")

            assistant_message["tool_calls"].append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": tool_call.function.arguments,
                    },
                }
            )
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )

        messages.append(assistant_message)
        messages.extend(tool_messages)

        if round_index == 3:
            raise RuntimeError("Tool loop exceeded the maximum number of rounds.")


if __name__ == "__main__":
    main()
