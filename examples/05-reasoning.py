#!/usr/bin/env python3
"""
Hy3 API Example 05 — Reasoning Mode（思考过程开/关对比）

用法：
    python 05-reasoning.py

前置条件：
    pip install openai
    Hy3 已通过 vLLM/SGLang 部署在 http://127.0.0.1:8000/v1
    启动时需要加: --reasoning-parser hy_v3
"""

import time
from openai import OpenAI

BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = [redacted]
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=[redacted])

MATH_PROBLEM = (
    "一个水池有两个进水管和一个出水管。进水管 A 单独注满需要 3 小时，"
    "进水管 B 单独注满需要 6 小时，出水管 C 单独排空需要 4 小时。"
    "如果三个管子同时打开，水池需要多久才能注满？"
)


def no_think():
    """关闭思考 — 直接回答"""
    print("=" * 60)
    print("  📝 Example 5.1 — 关闭思考 (reasoning_effort=no_think)")
    print("=" * 60)

    t0 = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": MATH_PROBLEM}],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )
    elapsed = time.time() - t0

    msg = response.choices[0].message
    print(f"  ⏱️  耗时: {elapsed:.2f}s")
    print(f"  📊 Tokens: {response.usage}")
    print(f"  💬 回答: {msg.content}")

    return elapsed, response.usage


def high_reasoning():
    """开启深度推理"""
    print("\n" + "=" * 60)
    print("  📝 Example 5.2 — 深度推理 (reasoning_effort=high)")
    print("=" * 60)

    t0 = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": MATH_PROBLEM}],
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
    )
    elapsed = time.time() - t0

    msg = response.choices[0].message
    # Hy3 思考模式下，思考过程存储在 reasoning_content
    reasoning = getattr(msg, "reasoning_content", "（无思考内容）")

    print(f"  ⏱️  耗时: {elapsed:.2f}s")
    print(f"  📊 Tokens: {response.usage}")
    print(f"  🧠 思考过程 ({len(reasoning)} 字):")
    for line in reasoning.split("\n")[:8]:
        print(f"     {line}")
    if len(reasoning.split("\n")) > 8:
        print(f"     ... (共 {len(reasoning.split(chr(10)))} 行)")
    print(f"\n  💬 最终回答: {msg.content}")

    return elapsed, response.usage


def comparison(t_nothink, t_high, usage_nothink, usage_high):
    """对比总结"""
    print("\n" + "=" * 60)
    print("  📊 思考模式对比")
    print("=" * 60)
    print(f"""
  ┌────────────┬───────────────┬───────────────┐
  │    模式     │  no_think     │  high          │
  ├────────────┼───────────────┼───────────────┤
  │  耗时       │  {t_nothink:.2f}s         │  {t_high:.2f}s         │
  │  总 tokens  │  {usage_nothink.total_tokens if usage_nothink else 'N/A':>13}  │  {usage_high.total_tokens if usage_high else 'N/A':>13}  │
  └────────────┴───────────────┴───────────────┘

  使用建议：
  - no_think: 日常对话、简单问答、翻译
  - low:      适度推理，平衡速度与质量
  - high:     数学、编程、复杂逻辑推理
  """)


if __name__ == "__main__":
    t1, u1 = no_think()
    t2, u2 = high_reasoning()
    comparison(t1, t2, u1, u2)
