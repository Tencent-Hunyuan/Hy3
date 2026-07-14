#!/usr/bin/env python3
"""
Hy3 API Example 02 — Streaming（流式请求 + 逐 chunk 解析）

用法：
    python 02-streaming.py

前置条件：
    pip install openai
    Hy3 已通过 vLLM/SGLang 部署在 http://127.0.0.1:8000/v1
"""

from openai import OpenAI

BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = [redacted]
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=[redacted])


def basic_streaming():
    """基础流式 — 逐 chunk 打印"""
    print("=" * 60)
    print("  📝 Example 2.1 — 流式输出")
    print("=" * 60)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "请用 50 字左右介绍 Python 语言。"},
        ],
        temperature=0.9,
        top_p=1.0,
        stream=True,
    )

    print("  🤖 Hy3: ", end="", flush=True)
    full_content = ""
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            text = chunk.choices[0].delta.content
            print(text, end="", flush=True)
            full_content += text
    print(f"\n\n  📊 总字符数: {len(full_content)}")

    # ── 期望输出（逐字打印） ────────────────
    #  🤖 Hy3: Python是一种高级、解释型、面向对象的编程语言，
    #  以其简洁清晰的语法和丰富的标准库著称...


def streaming_with_reasoning():
    """流式 + 思考过程 — 捕获 reasoning_content"""
    print("\n" + "=" * 60)
    print("  📝 Example 2.2 — 流式输出 + 思考过程 (reasoning_effort=high)")
    print("=" * 60)

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "一个长方形长 5 宽 3，它的对角线是多少？"},
        ],
        temperature=0.9,
        top_p=1.0,
        stream=True,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
    )

    reasoning = ""
    content = ""
    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta is None:
            continue
        # Hy3 reasoning 模式下，思考过程在 reasoning_content 字段
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            reasoning += delta.reasoning_content
        if delta.content:
            content += delta.content

    print(f"  🧠 思考过程 ({len(reasoning)} 字):")
    for line in reasoning.split("\n")[:5]:
        print(f"     {line}")
    if len(reasoning.split("\n")) > 5:
        print(f"     ... (共 {len(reasoning.split(chr(10)))} 行)")

    print(f"\n  💬 最终回答:")
    print(f"  {content}")

    # ── 期望输出 ──────────────────────────
    #  🧠 思考过程:
    #     我们需要使用勾股定理...
    #  💬 最终回答:
    #     对角线长度 ≈ 5.83


if __name__ == "__main__":
    basic_streaming()
    streaming_with_reasoning()
