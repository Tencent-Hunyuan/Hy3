from openai import OpenAI
import os
import json
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(
    api_key=os.getenv("API_KEY", "EMPTY"),
    base_url=os.getenv("BASE_URL", "http://127.0.0.1:8000/v1")
)


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，如北京、上海、广州"},
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
                    "expression": {"type": "string", "description": "数学表达式，如 3+5*2"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "获取指定股票的当前价格",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代码，如 AAPL、GOOGL"},
                },
                "required": ["symbol"],
            },
        },
    },
]


def mock_tool_call(tool_name, arguments):
    if tool_name == "get_weather":
        city = arguments.get("city", "")
        return f'{{"city": "{city}", "temperature": 25, "condition": "晴", "humidity": 60}}'
    elif tool_name == "calculate":
        expr = arguments.get("expression", "")
        try:
            result = eval(expr)
            return f'{{"expression": "{expr}", "result": {result}}}'
        except:
            return f'{{"expression": "{expr}", "result": "计算错误"}}'
    elif tool_name == "get_stock_price":
        symbol = arguments.get("symbol", "")
        return f'{{"symbol": "{symbol}", "price": 150.50, "change": "+2.3%"}}'
    return f'{{"error": "unknown tool: {tool_name}"}}'


def single_tool_call():
    print("=== 单次工具调用示例 ===")

    print("\n【完整请求参数】")
    print(f"  model: hy3")
    print(f"  messages: [{{'role': 'user', 'content': '北京今天天气怎么样？'}}]")
    print(f"  tools: [{len(tools)} 个工具]")

    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "user", "content": "北京今天天气怎么样？"},
        ],
        tools=tools,
    )

    print("\n【完整 Response 解析】")
    print(f"  id: {response.id}")
    print(f"  choices: {len(response.choices)}")

    choice = response.choices[0]
    print(f"  finish_reason: {choice.finish_reason}")

    message = choice.message
    print(f"  message.role: {message.role}")

    if message.tool_calls:
        print(f"  message.tool_calls:")
        for idx,tc in enumerate(response.choices[0].message.tool_calls):
            print(f"    [{idx}] id={tc.id}, type={tc.type}")
            print(f"      function.name: {tc.function.name}")
            print(f"      function.arguments: {tc.function.arguments}")

            args = json.loads(tc.function.arguments)
            tool_result = mock_tool_call(tc.function.name, args)
            print(f"      [模拟工具执行结果]: {tool_result}")


def multi_round_tool_loop():
    def get_role(msg):
        if isinstance(msg, dict):
            return msg.get("role")
        return msg.role
    print("\n\n=== 多轮工具循环示例 ===")

    messages = [
        {"role": "user", "content": "帮我计算一下：100乘以20%，然后用这个结果查询苹果公司的股票价格"},
    ]

    max_rounds = 5
    round_count = 0

    print("\n【完整对话流程】")
    print(f"初始问题: {messages[0]['content']}")

    while round_count < max_rounds:
        round_count += 1
        print(f"\n--- 第 {round_count} 轮 ---")

        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            tools=tools,
        )

        choice = response.choices[0]
        message = choice.message

        if choice.finish_reason == "tool_calls" and message.tool_calls:
            for tc in message.tool_calls:
                print(f"  工具调用: {tc.function.name}({tc.function.arguments})")

                args = json.loads(tc.function.arguments)
                tool_result = mock_tool_call(tc.function.name, args)
                print(f"  工具返回: {tool_result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })
        else:
            print(f"  最终回复: {message.content}")
            break

    print(f"\n【多轮工具循环总结】")
    print(f"  总轮数: {round_count}")
    tool_count = len([m for m in messages if get_role(m) == "tool"])
    print(f"  工具调用次数: {tool_count}")


if __name__ == "__main__":
    single_tool_call()
    multi_round_tool_loop()