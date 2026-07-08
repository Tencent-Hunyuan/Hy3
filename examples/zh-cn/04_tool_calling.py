"""Hy3 示例 04：工具调用。"""

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
        "condition": "多云间晴",
        "source": "模拟天气服务",
    }


def calculator(expression: str) -> Dict[str, Any]:
    allowed = set("0123456789+-*/(). %")
    if not set(expression) <= allowed:
        raise ValueError("表达式包含不支持的字符")
    return {"expression": expression, "result": eval(expression, {"__builtins__": {}}, {})}


TOOL_IMPLS = {"get_weather": get_weather, "calculator": calculator}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取某个城市的当前天气。本演示返回模拟数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "城市名称，例如 Beijing 或 Tokyo"},
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
            "description": "计算一个简单的算术表达式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "算术表达式，例如 (17 * 23) + 5"},
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
print("=== 单次工具解析 ===")
print("assistant 内容:", first_message.content)
print("工具调用:")
for tc in first_message.tool_calls or []:
    print("- 名称:", tc.function.name)
    print("  参数:", tc.function.arguments)

print("\n=== 多轮工具循环 ===")
messages = [{"role": "user", "content": "先查东京天气，再计算 17 * 23，最后把两个结果一起总结。"}]

for step in range(5):
    response = call_hy3(messages)
    message = response.choices[0].message
    tool_calls = message.tool_calls or []

    if not tool_calls:
        print("最终答案:", message.content)
        break

    print(f"第 {step + 1} 步: 模型请求 {len(tool_calls)} 次工具调用")
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

        print(f"已执行 {name}({args}) -> {result}")
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
else:
    print("已停止: 达到工具循环最大步数")
