"""
Hy3 API 示例 4：工具调用（Function Calling）
=============================================

演示两种工具调用模式：
  1. 单次工具调用 —— 模型选择调用工具，返回参数
  2. 多轮工具循环 —— 模型调工具 → 执行工具 → 返回结果 → 模型生成最终回答

前置条件：
  - 在 https://console.cloud.tencent.com/tokenhub/apikey 创建 API Key
  - 安装 openai: pip install openai

运行方式：
  python tool_calling.py
"""

import json
from openai import OpenAI

API_KEY = "sk-你的APIKey"  # TODO: 替换为真实的 API Key

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=API_KEY,
)

# ============================================================
# 1. 定义工具（Tools）
# ============================================================
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
                        "description": "城市名称，如 北京、上海、深圳",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位，默认为 celsius",
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
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 123 * 456",
                    },
                },
                "required": ["expression"],
            },
        },
    },
]


def execute_tool(tool_call):
    """模拟执行工具调用并返回结果"""
    fn_name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)

    if fn_name == "get_weather":
        city = args["city"]
        unit = args.get("unit", "celsius")
        # 模拟天气数据
        weather_data = {
            "北京": {"temperature": 28, "condition": "晴", "humidity": 45},
            "上海": {"temperature": 32, "condition": "多云", "humidity": 65},
            "深圳": {"temperature": 30, "condition": "阵雨", "humidity": 80},
        }
        info = weather_data.get(city, {"temperature": 25, "condition": "未知", "humidity": 50})
        return json.dumps({
            "city": city,
            "temperature": info["temperature"],
            "unit": unit,
            "condition": info["condition"],
            "humidity": info["humidity"],
        })

    elif fn_name == "calculate":
        try:
            import ast
            import operator as op
            OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
                   ast.Div: op.truediv, ast.FloorDiv: op.floordiv,
                   ast.Mod: op.mod, ast.Pow: op.pow}
            UOPS = {ast.UAdd: op.pos, ast.USub: op.neg}
            def _eval(node):
                if isinstance(node, ast.Expression):
                    return _eval(node.body)
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                    return node.value
                if isinstance(node, ast.BinOp) and type(node.op) in OPS:
                    return OPS[type(node.op)](_eval(node.left), _eval(node.right))
                if isinstance(node, ast.UnaryOp) and type(node.op) in UOPS:
                    return UOPS[type(node.op)](_eval(node.operand))
                raise ValueError("不支持的表达式")
            expr = args["expression"]
            result = _eval(ast.parse(expr, mode="eval"))
            return json.dumps({"expression": expr, "result": result})
        except Exception as e:
            return json.dumps({"error": str(e)})

    return json.dumps({"error": f"Unknown tool: {fn_name}"})


# ============================================================
# 2. 单次工具调用 —— 模型自动选择工具
# ============================================================
print("=" * 60)
print("【工具调用示例 1：单次调用】")
print("=" * 60)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "北京今天天气怎么样？"},
    ],
    temperature=0.7,
    top_p=1.0,
    tools=tools,
    tool_choice="auto",
    extra_body={"reasoning_effort": "no_think"},
)

message = response.choices[0].message

if message.tool_calls:
    for tc in message.tool_calls:
        print(f"\n模型选择调用工具: {tc.function.name}")
        print(f"参数: {tc.function.arguments}")

        # 执行工具
        result = execute_tool(tc)
        print(f"工具返回: {result}")
else:
    print(f"模型直接回答: {message.content}")

# ============================================================
# 3. 多轮工具循环 —— 模型 > 工具 > 模型 > ... > 最终回答
# ============================================================
print("\n\n" + "=" * 60)
print("【工具调用示例 2：多轮工具循环】")
print("=" * 60)

messages = [
    {"role": "system", "content": "你是一个有用的助手，可以使用工具来帮助用户。"},
    {"role": "user", "content": "帮我计算 12345 × 6789 的结果，然后查一下深圳的天气，最后用中文总结一下。"},
]

print(f"User: {messages[-1]['content']}\n")

MAX_TURNS = 5  # 防止无限循环

for turn in range(MAX_TURNS):
    print(f"--- 第 {turn + 1} 轮 ---")

    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.7,
        top_p=1.0,
        tools=tools,
        tool_choice="auto",
        extra_body={"reasoning_effort": "no_think"},
    )

    message = response.choices[0].message

    if message.tool_calls:
        # 将模型的工具调用请求加入 messages
        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ],
        })

        # 逐个执行工具并将结果加入 messages
        for tc in message.tool_calls:
            print(f"  🔧 调用工具: {tc.function.name}({tc.function.arguments})")
            result = execute_tool(tc)
            print(f"  ✅ 结果: {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })
    else:
        # 模型不再调用工具，输出最终回答
        print(f"\n  💬 最终回答:\n  {message.content}")
        break
else:
    print(f"\n  ⚠️ 达到最大轮数 {MAX_TURNS}，停止工具循环")

print(f"\n--- 完整消息历史共 {len(messages)} 条 ---")
for i, m in enumerate(messages):
    role = m["role"]
    content_preview = str(m.get("content", ""))[:60]
    has_tools = " (含工具调用)" if "tool_calls" in m else ""
    print(f"  [{i}] {role}: {content_preview}{has_tools}")
