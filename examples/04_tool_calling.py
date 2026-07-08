"""
Example 4: Tool Calling — single call & multi-round tool loop

Prerequisites:
  - Hy3 server running on port 8000
  - Server started with --enable-auto-tool-choice
  - pip install openai
"""

import json
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

tools = [
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
                        "description": "城市名称，如 北京、上海",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 2 + 3 * 4",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]

def execute_tool(name: str, args: dict) -> str:
    if name == "get_weather":
        city = args["city"]
        weather_db = {
            "北京": "晴，25°C，空气质量良",
            "上海": "多云，28°C，湿度 70%",
            "深圳": "阵雨，30°C，体感温度 34°C",
        }
        return json.dumps({"city": city, "weather": weather_db.get(city, "未知城市")})
    elif name == "calculate":
        try:
            result = eval(args["expression"])
            return json.dumps({"expression": args["expression"], "result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})
    return json.dumps({"error": f"未知工具: {name}"})

# 1. 单次 Tool Calling
print("=" * 60)
print("1. Single Tool Call")
print("=" * 60)

messages = [
    {"role": "user", "content": "北京的天气怎么样？"},
]

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    tools=tools,
    tool_choice="auto",
    temperature=0.7,
    max_tokens=512,
)

msg = response.choices[0].message

if msg.tool_calls:
    for tc in msg.tool_calls:
        print(f"\n工具调用: {tc.function.name}")
        print(f"参数: {tc.function.arguments}")
        args = json.loads(tc.function.arguments)
        result = execute_tool(tc.function.name, args)
        print(f"工具返回: {result}")

        messages.append(msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

    final = client.chat.completions.create(
        model="hy3",
        messages=messages,
        tools=tools,
        temperature=0.7,
        max_tokens=512,
    )
    print(f"\n最终回答: {final.choices[0].message.content}")
else:
    print(f"直接回答: {msg.content}")

# 2. 多轮 Tool Calling
print("\n" + "=" * 60)
print("2. Multi-round Tool Calling")
print("=" * 60)

messages = [
    {"role": "user", "content": "北京和上海今天天气怎么样？再帮我算一下 (25 + 17) * 3 的结果。"},
]

max_rounds = 5
for i in range(max_rounds):
    print(f"\n--- 第 {i+1} 轮 ---")
    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
        max_tokens=512,
    )
    msg = response.choices[0].message

    if not msg.tool_calls:
        print(f"最终回答: {msg.content}")
        break

    messages.append(msg)
    for tc in msg.tool_calls:
        print(f"调用工具: {tc.function.name}({tc.function.arguments})")
        args = json.loads(tc.function.arguments)
        result = execute_tool(tc.function.name, args)
        print(f"工具返回: {result}")
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })
else:
    print("达到最大轮数，停止循环")
