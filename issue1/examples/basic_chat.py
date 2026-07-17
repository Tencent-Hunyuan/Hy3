#!/usr/bin/env python3
"""
Hy3 基础对话示例：单轮对话与多轮对话。

使用方式：
    cd issue1
    python examples/basic_chat.py

前置条件：
    1. 复制 .env.example 为 .env 并填入 HY3_API_KEY
    2. pip install "openai>=1.0.0" python-dotenv
"""

import os
import sys
from pathlib import Path

# 将 issue1 目录加入路径，以便加载根目录的 .env
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ── 配置 ─────────────────────────────────────────────
BASE_URL = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
API_KEY = os.getenv("HY3_API_KEY", "")
MODEL = os.getenv("HY3_MODEL", "hy3-preview")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def chat(messages: list[dict], **kwargs) -> dict:
    """发送请求并返回解析后的关键字段。"""
    params = {
        "model": MODEL,
        "messages": messages,
        "temperature": kwargs.get("temperature", 0.9),
        "top_p": kwargs.get("top_p", 1.0),
        "max_tokens": kwargs.get("max_tokens", 256),
    }
    response = client.chat.completions.create(**params)
    choice = response.choices[0]
    return {
        "id": response.id,
        "model": response.model,
        "finish_reason": choice.finish_reason,
        "content": choice.message.content,
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        },
    }


def main():
    print("=" * 60)
    print("【示例 1】单轮对话")
    print("=" * 60)

    single_messages = [
        {"role": "user", "content": "请用一句话介绍腾讯混元 Hy3 模型。"}
    ]
    print(f"\n请求 messages:\n{single_messages}\n")

    result = chat(single_messages, temperature=0.9, max_tokens=128)
    print(f"模型: {result['model']}")
    print(f"完成原因: {result['finish_reason']}")
    print(f"回复: {result['content']}")
    print(f"Token 用量: {result['usage']}")

    # ── 多轮对话 ─────────────────────────────────────
    print("\n" + "=" * 60)
    print("【示例 2】多轮对话")
    print("=" * 60)

    multi_messages = [
        {"role": "user", "content": "请用一句话介绍腾讯混元 Hy3 模型。"},
        {"role": "assistant", "content": result["content"]},
        {
            "role": "user",
            "content": "那么它在代码生成方面有什么优势？请列出 3 点。",
        },
    ]
    print(f"\n请求 messages（含历史上下文）:\n{multi_messages[:2]}")  # 只展示前两条
    print(f"... (共 {len(multi_messages)} 条消息)\n")

    result2 = chat(multi_messages, temperature=0.7, max_tokens=256)
    print(f"模型: {result2['model']}")
    print(f"完成原因: {result2['finish_reason']}")
    print(f"回复: {result2['content']}")
    print(f"Token 用量: {result2['usage']}")

    print("\n✅ basic_chat 示例运行完成！")


if __name__ == "__main__":
    main()
