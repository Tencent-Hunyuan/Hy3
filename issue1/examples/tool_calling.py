#!/usr/bin/env python3
"""
Hy3 工具调用 (Function Calling) 示例：单次调用与多轮工具循环。

使用方式：
    cd issue1
    python examples/tool_calling.py

前置条件：
    1. 复制 .env.example 为 .env 并填入 HY3_API_KEY
    2. pip install "openai>=1.0.0" python-dotenv
"""

import os
import sys
import json
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
API_KEY = os.getenv("HY3_API_KEY", "")
MODEL = os.getenv("HY3_MODEL", "hy3-preview")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ── 工具定义 ─────────────────────────────────────────

WEATHER_DB = {
    "深圳": {"city": "深圳", "condition": "小雨", "temp_c": 29, "humidity": 82, "umbrella": True},
    "北京": {"city": "北京", "condition": "晴", "temp_c": 24, "humidity": 40, "umbrella": False},
    "上海": {"city": "上海", "condition": "多云", "temp_c": 26, "humidity": 65, "umbrella": False},
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气信息。支持深圳、北京、上海。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 深圳、北京、上海",
                    }
                },
                "required": ["city"],
            },
        },
    }
]

MAX_ROUNDS = 4  # 最大工具调用轮次，防止死循环


def get_weather(city: str) -> dict:
    """模拟天气查询工具。"""
    return WEATHER_DB.get(
        city,
        {"city": city, "error": "该城市不在示例数据中，请尝试深圳、北京或上海。"},
    )


def execute_tool(tool_name: str, args: dict) -> dict:
    """工具调度器。"""
    if tool_name == "get_weather":
        return get_weather(args.get("city", ""))
    return {"error": f"未知工具: {tool_name}"}


def main():
    print("=" * 60)
    print("【Hy3 Function Calling — 工具调用示例】")
    print("=" * 60)

    messages = [
        {
            "role": "user",
            "content": "请帮我查一下深圳的天气，然后告诉我是否需要带伞。",
        }
    ]

    print(f"\n用户提问: {messages[0]['content']}")
    print(f"可用工具: get_weather(深圳/北京/上海)\n")

    for round_idx in range(1, MAX_ROUNDS + 1):
        print(f"─" * 40)
        print(f"第 {round_idx} 轮请求")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,  # 工具调用场景推荐低温度
            top_p=1.0,
            max_tokens=512,
        )

        choice = response.choices[0]
        message = choice.message
        tool_calls = getattr(message, "tool_calls", None) or []

        print(f"  finish_reason: {choice.finish_reason}")
        print(f"  content: {message.content}")
        print(f"  tool_calls 数量: {len(tool_calls)}")

        if not tool_calls:
            # 模型认为不需要调工具，直接输出最终回答
            print(f"\n{'=' * 60}")
            print(f"【最终回答】")
            print(f"{'=' * 60}")
            print(message.content)
            print(f"\n✅ tool_calling 示例运行完成！")
            return

        # 记录 assistant 消息（含 tool_calls）
        tc_data = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in tool_calls
        ]
        messages.append({"role": "assistant", "content": message.content, "tool_calls": tc_data})

        # 执行每个工具调用
        for tc in tool_calls:
            func_name = tc.function.name
            try:
                func_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            print(f"\n  🔧 调用工具: {func_name}({json.dumps(func_args, ensure_ascii=False)})")

            result = execute_tool(func_name, func_args)
            print(f"  📋 工具返回: {json.dumps(result, ensure_ascii=False)}")

            # 将工具结果加入消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    print("\n⚠️ 达到最大工具调用轮次限制，可能需要检查工具定义或模型行为。")
    print("\n✅ tool_calling 示例运行完成！")


if __name__ == "__main__":
    main()
