#!/usr/bin/env python3
"""
Hy3 流式请求示例：stream=True 下的逐 chunk 解析。

使用方式：
    cd issue1
    python examples/streaming.py

前置条件：
    1. 复制 .env.example 为 .env 并填入 HY3_API_KEY
    2. pip install "openai>=1.0.0" python-dotenv
"""

import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
API_KEY = os.getenv("HY3_API_KEY", "")
MODEL = os.getenv("HY3_MODEL", "hy3-preview")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def main():
    print("=" * 60)
    print("【流式请求 (stream=True) 逐 chunk 解析】")
    print("=" * 60)

    messages = [
        {
            "role": "user",
            "content": "请列出验证 Hy3 API 集成的 4 个关键步骤，每步一句话。",
        }
    ]

    print(f"\n请求 messages: {json.dumps(messages, ensure_ascii=False, indent=2)}\n")

    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,
        top_p=1.0,
        max_tokens=256,
        stream=True,
    )

    content_parts: list[str] = []
    reasoning_parts: list[str] = []

    print("─" * 60)
    print(f"{'chunk':>5s} {'role':<12s} {'content':<40s} {'finish_reason'}")
    print("─" * 60)

    for idx, chunk in enumerate(stream):
        if not chunk.choices:
            continue

        choice = chunk.choices[0]
        delta = choice.delta
        role = getattr(delta, "role", None)
        content = getattr(delta, "content", None)
        reasoning = getattr(delta, "reasoning_content", None)
        finish = choice.finish_reason

        if content:
            content_parts.append(content)
        if reasoning:
            reasoning_parts.append(reasoning)

        # 截断显示内容，避免刷屏
        display_content = (content or "")[:35] + ("..." if content and len(content) > 35 else "")
        print(f"{idx:>5d} {str(role):<12s} {display_content:<40s} {str(finish)}")

    print("─" * 60)

    full_content = "".join(content_parts)
    full_reasoning = "".join(reasoning_parts)

    print(f"\n完整回复 ({len(content_parts)} 个 content chunk):")
    print(full_content)
    if full_reasoning:
        print(f"\n思考过程 ({len(reasoning_parts)} 个 reasoning chunk):")
        print(full_reasoning)

    print(f"\n✅ streaming 示例运行完成！")


if __name__ == "__main__":
    main()
