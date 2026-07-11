"""
Hy3 API - 工具调用示例 / Tool Calling Example
包含单次工具调用和多轮工具循环
"""

import json
from openai import OpenAI

# ============================================================
# 配置 / Configuration
# ============================================================
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ============================================================
# 工具定义 / Tool Definitions
# ============================================================
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
                        "description": "城市名称，如 '北京'、'上海'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位，默认 celsius",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算并返回结果",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Python 可执行的数学表达式，如 '2 + 3 * 4'",
                    },
                },
                "required": ["expression"],
            },
        },
    },
]


# ============================================================
# 工具执行模拟 / Mock Tool Execution
# ============================================================
def execute_tool(tool_call) -> str:
    """根据工具名称模拟执行并返回 JSON 结果"""
    name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    if name == "get_weather":
        # 模拟天气数据
        weather_data = {
            "北京": {"temperature": 22, "humidity": 65, "condition": "晴"},
            "上海": {"temperature": 26, "humidity": 80, "condition": "多云"},
            "广州": {"temperature": 30, "humidity": 85, "condition": "雷阵雨"},
        }
        city = args["city"]
        data = weather_data.get(city, {"temperature": 20, "humidity": 50, "condition": "未知"})
        return json.dumps({"city": city, **data}, ensure_ascii=False)

    elif name == "calculate":
        try:
            result = eval(args["expression"])  # 仅用于演示，生产环境请使用安全解析
            return json.dumps({"expression": args["expression"], "result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})

    return json.dumps({"error": f"未知工具: {name}"})


# ============================================================
# 示例 1：单次工具调用 / Single Tool Call
# ============================================================
def single_tool_call():
    """用户提问触发单个工具，返回工具结果后生成最终回复"""
    print("=" * 60)
    print("单次工具调用 / Single Tool Call")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "北京今天天气怎么样？"},
    ]

    # 第一轮：模型决定调用工具
    print("\n[Round 1] 发送用户请求...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        temperature=0.9,
        top_p=1.0,
    )

    msg = response.choices[0].message

    # 检查是否触发了工具调用
    if not msg.tool_calls:
        print(f"模型直接回复（无工具调用）：{msg.content}")
        return

    # 打印工具调用信息
    for tc in msg.tool_calls:
        print(f"  调用工具：{tc.function.name}")
        print(f"  参数：{tc.function.arguments}")

    # 将助手消息（含 tool_calls）加入历史
    messages.append(msg)

    # 执行工具并返回结果
    for tc in msg.tool_calls:
        result = execute_tool(tc)
        print(f"  工具结果：{result}")
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

    # 第二轮：模型基于工具结果生成最终回复
    print("\n[Round 2] 将工具结果返回给模型...")
    final_response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        temperature=0.9,
        top_p=1.0,
    )
    print(f"  最终回复：{final_response.choices[0].message.content}")


# ============================================================
# 示例 2：多轮工具循环 / Multi-Round Tool Loop
# ============================================================
def multi_round_tool_loop():
    """复杂问题需要多次工具调用才能得出最终答案"""
    print("\n" + "=" * 60)
    print("多轮工具循环 / Multi-Round Tool Loop")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "查一下北京和上海的天气，然后计算两地的温差。"},
    ]

    max_rounds = 5  # 防止无限循环

    for round_num in range(1, max_rounds + 1):
        print(f"\n[Round {round_num}] 发送请求...")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            temperature=0.9,
            top_p=1.0,
        )

        msg = response.choices[0].message

        # 无工具调用 → 最终回复
        if not msg.tool_calls:
            print(f"  最终回复：{msg.content}")
            break

        # 追加助手消息
        messages.append(msg)

        # 执行所有工具调用
        for tc in msg.tool_calls:
            print(f"  调用工具：{tc.function.name}({tc.function.arguments})")
            result = execute_tool(tc)
            print(f"  工具结果：{result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    else:
        print("  达到最大轮次限制。")


# ============================================================
# 示例 3：并行工具调用 / Parallel Tool Calls
# ============================================================
def parallel_tool_calls():
    """模型可能在一次响应中同时请求多个工具"""
    print("\n" + "=" * 60)
    print("并行工具调用 / Parallel Tool Calls")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "同时查一下北京、上海和广州的天气。"},
    ]

    print("\n[Round 1] 发送请求...")
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        temperature=0.9,
        top_p=1.0,
    )

    msg = response.choices[0].message

    if not msg.tool_calls:
        print(f"  模型直接回复：{msg.content}")
        return

    print(f"  模型同时请求了 {len(msg.tool_calls)} 个工具调用：")
    messages.append(msg)

    for tc in msg.tool_calls:
        result = execute_tool(tc)
        print(f"    - {tc.function.name}({tc.function.arguments}) → {result}")
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": result,
        })

    print("\n[Round 2] 返回所有工具结果...")
    final_response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        temperature=0.9,
        top_p=1.0,
    )
    print(f"  最终回复：{final_response.choices[0].message.content}")


# ============================================================
# 运行示例
# ============================================================
if __name__ == "__main__":
    single_tool_call()
    multi_round_tool_loop()
    parallel_tool_calls()
