#!/usr/bin/env python3
"""
Hy3 API Example 04 — Tool Calling（一次调用 + 多轮工具循环）

用法：
    python 04-tool-calling.py

前置条件：
    pip install openai
    Hy3 已通过 vLLM/SGLang 部署在 http://127.0.0.1:8000/v1
    启动时需要加: --tool-call-parser hy_v3 --enable-auto-tool-choice
"""

import json
from openai import OpenAI

BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = [redacted]
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=[redacted])


# ─── 定义工具 ────────────────────────────
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
                        "description": "城市名称，如 Beijing, Shanghai",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "执行数学计算，支持 add/subtract/multiply/divide/power",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide", "power"],
                    },
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["operation", "a", "b"],
            },
        },
    },
]

# ─── 工具实现（模拟） ───────────────────
def get_weather(city: str, unit: str = "celsius") -> str:
    """模拟天气查询"""
    weather_data = {
        "beijing": {"celsius": "5°C 晴朗", "fahrenheit": "41°F Sunny"},
        "shanghai": {"celsius": "12°C 多云", "fahrenheit": "54°F Cloudy"},
    }
    return weather_data.get(city.lower(), {}).get(unit, f"{city}: 暂无数据")


def calculator(operation: str, a: float, b: float) -> str:
    ops = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: "除数不能为 0" if y == 0 else x / y,
        "power": lambda x, y: x ** y,
    }
    result = ops[operation](a, b)
    return str(result)


def execute_tool(name: str, args: dict) -> str:
    if name == "get_weather":
        return get_weather(**args)
    elif name == "calculator":
        return calculator(**args)
    return f"未知工具: {name}"


def single_tool_call():
    """一次工具调用 — LLM 自动决定调用哪个工具"""
    print("=" * 60)
    print("  📝 Example 4.1 — 一次 Tool Call")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "北京今天天气怎么样？"},
        ],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0.9,
        top_p=1.0,
    )

    msg = response.choices[0].message

    if msg.tool_calls:
        for tc in msg.tool_calls:
            fn = tc.function
            args = json.loads(fn.arguments)
            result = execute_tool(fn.name, args)
            print(f"  🔧 调用工具: {fn.name}({args})")
            print(f"  📊 返回结果: {result}")
    else:
        print(f"  💬 直接回答: {msg.content}")

    # ── 期望输出 ──────────────────────────
    #  🔧 调用工具: get_weather({'city': 'Beijing'})
    #  📊 返回结果: 5°C 晴朗


def multi_turn_tool_loop():
    """多轮工具循环 — LLM 多次调用工具直到得到最终答案"""
    print("\n" + "=" * 60)
    print("  📝 Example 4.2 — 多轮 Tool Call 循环 (ReAct)")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "北京和上海哪个更暖和？如果北京温度乘以 3 等于多少？"},
    ]

    for turn in range(5):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.9,
            top_p=1.0,
        )
        msg = response.choices[0].message
        messages.append(msg)

        if msg.tool_calls:
            for tc in msg.tool_calls:
                fn = tc.function
                args = json.loads(fn.arguments)
                result = execute_tool(fn.name, args)
                print(f"  🔄 第{turn+1}轮 → {fn.name}({args}) = {result}")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            print(f"\n  🤖 最终回答: {msg.content}")
            break

    # ── 期望输出 ──────────────────────────
    #  🔄 第1轮 → get_weather({'city': 'Beijing'}) = 5°C 晴朗
    #  🔄 第2轮 → get_weather({'city': 'Shanghai'}) = 12°C 多云
    #  🔄 第3轮 → calculator({'operation': 'multiply', 'a': 5, 'b': 3}) = 15
    #  🤖 最终回答: 上海(12°C)比北京(5°C)更暖和，北京温度乘以3等于15。


if __name__ == "__main__":
    single_tool_call()
    multi_turn_tool_loop()
