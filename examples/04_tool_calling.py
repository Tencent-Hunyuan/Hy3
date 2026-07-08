"""Hy3 example 04: tool calling."""

import json
import os
from typing import Any, Dict
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120.0)


def get_weather(location: str, unit: str = "celsius") -> Dict[str, Any]:
    return {
        "location": location,
        "unit": unit,
        "temperature": 21 if unit == "celsius" else 70,
        "condition": "partly cloudy",
        "source": "mock-weather-service",
    }


def calculator(expression: str) -> Dict[str, Any]:
    allowed = set("0123456789+-*/(). %")
    if not set(expression) <= allowed:
        raise ValueError("expression contains unsupported characters")
    return {"expression": expression, "result": eval(expression, {"__builtins__": {}}, {})}


TOOL_IMPLS = {"get_weather": get_weather, "calculator": calculator}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city. This demo returns mock data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name, e.g. Beijing or Tokyo"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location", "unit"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a simple arithmetic expression.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Arithmetic expression, e.g. (17 * 23) + 5"},
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]


def tool_call_to_message(tool_call):
    return {
        "id": tool_call.id,
        "type": "function",
        "function": {"name": tool_call.function.name, "arguments": tool_call.function.arguments},
    }


def call_hy3(messages):
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        parallel_tool_calls=False,
        temperature=0.2,
        max_tokens=800,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )


messages = [{"role": "user", "content": "东京现在天气怎么样？请调用工具查询，并用摄氏度回答。"}]
first = call_hy3(messages)
first_message = first.choices[0].message
print("=== one-call tool parsing ===")
print("assistant content:", first_message.content)
print("tool_calls:")
for tc in first_message.tool_calls or []:
    print("- name:", tc.function.name)
    print("  arguments:", tc.function.arguments)

print("\n=== multi-turn tool loop ===")
messages = [{"role": "user", "content": "先查东京天气，再计算 17 * 23，最后把两个结果一起总结。"}]

for step in range(5):
    response = call_hy3(messages)
    message = response.choices[0].message
    tool_calls = message.tool_calls or []

    if not tool_calls:
        print("final answer:", message.content)
        break

    print(f"step {step + 1}: model requested {len(tool_calls)} tool call(s)")
    messages.append(
        {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [tool_call_to_message(tc) for tc in tool_calls],
        }
    )

    for tc in tool_calls:
        name = tc.function.name
        args = json.loads(tc.function.arguments or "{}")
        try:
            result = TOOL_IMPLS[name](**args)
        except Exception as exc:
            result = {"error": str(exc), "tool": name, "args": args}

        print(f"executed {name}({args}) -> {result}")
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
else:
    print("stopped: reached max tool-loop steps")
