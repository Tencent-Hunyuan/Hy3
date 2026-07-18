"""04 tool calling: one-shot tools + multi-turn tool loop."""
import json
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询城市天气（演示用假数据）",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如 北京"},
                },
                "required": ["city"],
            },
        },
    }
]


def fake_get_weather(city: str) -> str:
    return json.dumps({"city": city, "weather": "晴", "temp_c": 26}, ensure_ascii=False)


def once_tool_call():
    print("=== one-shot tool call ===")
    messages = [{"role": "user", "content": "北京今天天气怎么样？请调用工具查询。"}]
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=256,
        temperature=0.2,
    )
    msg = resp.choices[0].message
    print("content:", msg.content)
    print("tool_calls:", msg.tool_calls)
    return resp


def multi_turn_tool_loop():
    print("\n=== multi-turn tool loop ===")
    messages = [{"role": "user", "content": "查询上海的天气，并用一句话总结。"}]
    # round 1: model may request tool
    r1 = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
        max_tokens=256,
        temperature=0.2,
    )
    m1 = r1.choices[0].message
    print("round1 content:", m1.content)
    print("round1 tool_calls:", m1.tool_calls)

    # append assistant message (with tool_calls if any)
    assistant_msg = {
        "role": "assistant",
        "content": m1.content or "",
    }
    if m1.tool_calls:
        assistant_msg["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in m1.tool_calls
        ]
    messages.append(assistant_msg)

    if not m1.tool_calls:
        print("模型未返回 tool_calls（云端/本地若未开 tool parser 时可能发生）。结束演示。")
        return r1

    for tc in m1.tool_calls:
        name = tc.function.name
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {}
        if name == "get_weather":
            result = fake_get_weather(args.get("city", "未知"))
        else:
            result = json.dumps({"error": f"unknown tool {name}"})
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            }
        )
        print("tool result:", result)

    r2 = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
        max_tokens=256,
        temperature=0.2,
    )
    print("round2 final:", r2.choices[0].message.content)
    return r2


if __name__ == "__main__":
    once_tool_call()
    multi_turn_tool_loop()
