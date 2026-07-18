"""
04 · tool calling —— 一次调用 + 多轮工具循环
演示 function calling: 模型自主决定调用工具, 执行后回填, 多轮直到产出最终回答。
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import get_client, MODEL

client = get_client()

# ── 定义工具 (OpenAI function calling 格式) ─────────────
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的实时天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名, 例如 北京"},
            },
            "required": ["city"],
        },
    },
}]


def get_weather(city: str) -> dict:
    """模拟工具实现 (真实场景里这里调天气 API)。"""
    db = {"北京": {"temp_c": 31, "weather": "晴"}, "上海": {"temp_c": 28, "weather": "多云"}}
    return db.get(city, {"temp_c": 25, "weather": "未知"})


# ── 多轮工具循环 ────────────────────────────────────────
messages = [{"role": "user", "content": "北京和上海今天分别多少度? 帮我对比"}]

print("=== 第一轮: 让模型决定调用哪些工具 ===")
resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
msg = resp.choices[0].message
messages.append(msg)
print("tool_calls:", [tc.function.name for tc in msg.tool_calls] if msg.tool_calls else None)

# 执行工具并回填, 进入下一轮
round_n = 1
while msg.tool_calls:
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)
        print(f"\n[执行工具] {tc.function.name}({args})")
        result = get_weather(**args)
        print(f"[工具返回] {result}")
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False),
        })
    round_n += 1
    print(f"\n=== 第 {round_n} 轮 ===")
    resp = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
    msg = resp.choices[0].message
    messages.append(msg)

print("\n=== 最终回答 ===")
print(msg.content)
