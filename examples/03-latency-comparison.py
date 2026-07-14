#!/usr/bin/env python3
"""
Hy3 API Example 03 — Non-Streaming vs Streaming 时延对比

用法：
    python 03-latency-comparison.py

前置条件：
    pip install openai
    Hy3 已通过 vLLM/SGLang 部署在 http://127.0.0.1:8000/v1
"""

import time
from openai import OpenAI

BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = [redacted]
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=[redacted])

PROMPT = "请用大约100字介绍人工智能的发展历史。"


def non_streaming():
    """非流式：等待全部 token 生成完再返回"""
    print("=" * 60)
    print("  📝 Example 3.1 — 非流式（non-streaming）")
    print("=" * 60)

    t0 = time.time()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        stream=False,
    )
    total_time = time.time() - t0

    content = response.choices[0].message.content
    tokens = response.usage.completion_tokens if response.usage else 0
    print(f"  🤖 {content}")
    print(f"\n  ⏱️  总耗时: {total_time:.2f}s")
    print(f"  📊 输出 tokens: {tokens}")


def streaming():
    """流式：逐 chunk 返回，可以测量首 token 时延"""
    print("\n" + "=" * 60)
    print("  📝 Example 3.2 — 流式（streaming）")
    print("=" * 60)

    t0 = time.time()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        stream=True,
    )

    first_token_time = None
    chunk_count = 0
    content = ""

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if first_token_time is None:
                first_token_time = time.time() - t0
            content += chunk.choices[0].delta.content
            chunk_count += 1

    total_time = time.time() - t0

    print(f"  🤖 {content}")
    print(f"\n  ⏱️  首 token 时延 (TTFT): {first_token_time:.2f}s" if first_token_time else "")
    print(f"  ⏱️  总耗时: {total_time:.2f}s")
    print(f"  📊 Chunk 数量: {chunk_count}")

    # ── 期望输出 ──────────────────────────
    #  ⏱️  首 token 时延 (TTFT): 0.35s
    #  ⏱️  总耗时: 2.18s
    #  📊 Chunk 数量: 15


def comparison():
    """并排对比"""
    print("\n" + "=" * 60)
    print("  📊 对比总结")
    print("=" * 60)
    print("""
  ┌──────────────────┬─────────────────────┐
  │  non-streaming   │  streaming          │
  ├──────────────────┼─────────────────────┤
  │  等全部生成完才返回  │  逐 token 实时返回      │
  │  用户体验: 白屏等待  │  用户体验: 打字机效果    │
  │  首 token 时延: 不可测│  首 token 时延: 可测量  │
  │  适合: 批处理       │  适合: 聊天/交互        │
  └──────────────────┴─────────────────────┘

  关键指标：
  - TTFT (Time to First Token): 流式模式下首 token 到达时间
  - TPOT (Time per Output Token): 每个 token 的生成间隔
  - 总耗时 ≈ TTFT + TPOT × token 数
  """)


if __name__ == "__main__":
    non_streaming()
    streaming()
    comparison()
