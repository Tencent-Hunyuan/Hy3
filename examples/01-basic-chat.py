#!/usr/bin/env python3
"""
Hy3 API Example 01 — Basic Chat（单轮 + 多轮对话）

用法：
    python 01-basic-chat.py

前置条件：
    pip install openai
    Hy3 已通过 vLLM/SGLang 部署在 http://127.0.0.1:8000/v1
"""

from openai import OpenAI

# ─── 配置 ──────────────────────────────────
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "[redacted]"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=[redacted])


def single_turn():
    """单轮对话 — 一问一答"""
    print("=" * 60)
    print("  📝 Example 1.1 — 单轮对话")
    print("=" * 60)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "用一句话介绍腾讯混元大模型 Hy3。"},
        ],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )

    print(f"  💬 User: 用一句话介绍腾讯混元大模型 Hy3。")
    print(f"  🤖 Hy3: {response.choices[0].message.content}")
    print(f"  📊 Usage: {response.usage}")

    # ── 期望输出 ──────────────────────────
    #  🤖 Hy3: 腾讯混元大模型 Hy3 是一个 295B 参数的 ...
    #  📊 Usage: CompletionUsage(completion_tokens=..., prompt_tokens=..., total_tokens=...)


def multi_turn():
    """多轮对话 — 上下文连续"""
    print("\n" + "=" * 60)
    print("  📝 Example 1.2 — 多轮对话")
    print("=" * 60)

    messages = []

    # 第一轮
    messages.append({"role": "user", "content": "我叫小明，我今年 25 岁。"})
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
    )
    messages.append(resp.choices[0].message)

    # 第二轮（引用上文）
    messages.append({"role": "user", "content": "我叫什么名字？我几岁？"})
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
    )

    for i, msg in enumerate(messages):
        role = "👤" if msg["role"] == "user" else "🤖"
        content = msg.content if hasattr(msg, "content") else msg["content"]
        print(f"  {role} [{msg['role']}]: {content}")

    # ── 期望输出 ──────────────────────────
    #  👤 [user]: 我叫小明，我今年 25 岁。
    #  🤖 [assistant]: 好的，小明...
    #  👤 [user]: 我叫什么名字？我几岁？
    #  🤖 [assistant]: 你叫小明，今年 25 岁。（模型记住了上文信息）


def multi_turn_with_system():
    """多轮对话 + system prompt — 人格设定"""
    print("\n" + "=" * 60)
    print("  📝 Example 1.3 — 多轮对话 + System Prompt")
    print("=" * 60)

    messages = [
        {"role": "system", "content": "你是一个幽默的 AI 助手，每次回答都以一个笑话开头。"},
        {"role": "user", "content": "今天天气真好。"},
    ]

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
    )

    print(f"  🧑‍💻 System: 你是一个幽默的 AI 助手...")
    print(f"  👤 User: 今天天气真好。")
    print(f"  🤖 Hy3: {response.choices[0].message.content}")

    # ── 期望输出 ──────────────────────────
    #  🤖 Hy3: 为什么太阳要去上班？因为它是"日"光族！——说回天气...


if __name__ == "__main__":
    single_turn()
    multi_turn()
    multi_turn_with_system()
