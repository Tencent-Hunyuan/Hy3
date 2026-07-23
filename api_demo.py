"""
腾讯混元 Hy3 API 调用示例
使用 OpenAI 兼容接口，支持普通对话、深度推理、Function Calling 等模式。
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url=os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"),
)

MODEL = os.getenv("HY3_MODEL", "hy3-preview")


def chat(prompt: str, reasoning_effort: str = "no_think") -> str:
    """
    普通对话 / 深度推理

    Args:
        prompt: 用户输入
        reasoning_effort: "no_think" (直接回复), "low", "high" (深度思维链)
    """
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning_effort}},
    )
    return response.choices[0].message.content


def chat_stream(prompt: str, reasoning_effort: str = "no_think"):
    """流式对话（逐字输出）"""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        top_p=1.0,
        stream=True,
        extra_body={"chat_template_kwargs": {"reasoning_effort": reasoning_effort}},
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()


def chat_with_tools(prompt: str, tools: list[dict]) -> dict:
    """带 Function Calling 的对话"""
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        temperature=0.9,
        top_p=1.0,
    )
    return response.choices[0].message


# ─── 使用示例 ─────────────────────────────────────────────

if __name__ == "__main__":
    # 1. 普通对话（无推理）
    print("=" * 60)
    print("【普通对话】")
    print("=" * 60)
    result = chat("你好！请用一句话介绍你自己。")
    print(result)
    print()

    # 2. 深度推理（复杂任务）
    print("=" * 60)
    print("【深度推理 - 数学题】")
    print("=" * 60)
    result = chat(
        "设 f(x) = x³ - 6x² + 11x - 6，求 f(x) 在区间 [0, 4] 上的最大值和最小值。",
        reasoning_effort="high",
    )
    print(result)
    print()

    # 3. Function Calling 示例
    print("=" * 60)
    print("【Function Calling - 获取天气】")
    print("=" * 60)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取指定城市的天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"},
                    },
                    "required": ["city"],
                },
            },
        }
    ]
    msg = chat_with_tools("北京今天天气怎么样？", tools)
    print(f"tool_calls: {msg.tool_calls}")
    print()
    print("所有示例运行完成！")
