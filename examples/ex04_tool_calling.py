"""
ex04_tool_calling.py
单次工具调用与多轮工具循环示例
"""

import os
import json
from openai import OpenAI


def create_client():
    return OpenAI(
        api_key=os.environ.get("HY3_API_KEY"),
        base_url="https://tokenhub.tencentmaas.com/v1",
    )


def get_weather(city: str) -> str:
    """模拟查询天气"""
    weather_db = {
        "北京": "晴朗，25°C",
        "上海": "多云，28°C",
        "深圳": "小雨，30°C",
    }
    return weather_db.get(city, f"暂无 {city} 的天气数据")


def run_tool_loop(client: OpenAI, user_question: str, max_rounds: int = 3):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询指定城市的天气",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称，如北京、上海、深圳",
                        }
                    },
                    "required": ["city"],
                },
            },
        }
    ]

    messages = [
        {"role": "system", "content": "你可以调用 get_weather 工具查询天气。"},
        {"role": "user", "content": user_question},
    ]

    for round_idx in range(max_rounds):
        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.3,
        )

        message = response.choices[0].message
        print(f"\n=== Round {round_idx + 1} ===")
        print("content:", message.content)
        print("tool_calls:", message.tool_calls)

        # 将 assistant 消息（含 tool_calls）转换为 dict 后追加到上下文
        messages.append(message.model_dump())

        if not message.tool_calls:
            print("\n模型已给出最终回答，无需继续调用工具。")
            return message.content

        # 执行所有工具调用
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"调用工具: {function_name}({function_args})")

            if function_name == "get_weather":
                result = get_weather(**function_args)
            else:
                result = f"未知工具: {function_name}"

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    print("\n达到最大轮次，补充一次最终调用获取总结。")
    final_response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.3,
    )
    return final_response.choices[0].message.content


if __name__ == "__main__":
    client = create_client()
    answer = run_tool_loop(client, "今天北京和深圳的天气怎么样？")
    print("\n最终回答:", answer)
