"""
04 - Tool Calling
演示一次工具调用与多轮工具循环

Usage:
  export HY3_BASE_URL=http://127.0.0.1:8000/v1
  export HY3_API_KEY=EMPTY
  export HY3_MODEL=hy3
  python tool_calling.py
"""

import json
from openai import OpenAI
import os

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# 模拟天气查询函数
def get_weather(city: str) -> dict:
    data = {
        "北京": {"temperature": 28, "condition": "晴", "humidity": 45},
        "上海": {"temperature": 30, "condition": "多云", "humidity": 65},
        "广州": {"temperature": 32, "condition": "雷阵雨", "humidity": 80},
        "深圳": {"temperature": 31, "condition": "阴", "humidity": 75},
    }
    return data.get(city, {"temperature": 25, "condition": "未知", "humidity": 50})

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，如北京、上海"}
                },
                "required": ["city"]
            },
        }
    }
]

messages = [
    {"role": "user", "content": "北京和上海今天天气怎么样？哪个更暖和？"},
]

print("=" * 50)
print("多轮工具循环")
print("=" * 50)

while True:
    response = client.chat.completions.create(
        model=MODEL, messages=messages, tools=tools, tool_choice="auto",
    )
    message = response.choices[0].message
    messages.append(message)

    if not message.tool_calls:
        print(f"\n最终回复: {message.content}")
        break

    for tc in message.tool_calls:
        print(f"\n调用工具: {tc.function.name}")
        print(f"参数: {tc.function.arguments}")

        args = json.loads(tc.function.arguments)
        result = get_weather(args["city"])
        result_str = json.dumps(result, ensure_ascii=False)

        print(f"工具返回: {result_str}")

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result_str,
        })
