#!/usr/bin/env python3
"""
Hy3 非流式 vs 流式时延对比。

使用方式：
    cd issue1
    python examples/latency_compare.py

前置条件：
    1. 复制 .env.example 为 .env 并填入 HY3_API_KEY
    2. pip install "openai>=1.0.0" python-dotenv
"""

import os
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1")
API_KEY = os.getenv("HY3_API_KEY", "")
MODEL = os.getenv("HY3_MODEL", "hy3-preview")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=60.0)

MESSAGES = [
    {
        "role": "user",
        "content": "请列出将 Hy3 API 客户端投入生产环境的 5 项检查清单，每项一句话。",
    }
]


def test_non_streaming():
    """非流式请求：测量总耗时。"""
    print("\n" + "=" * 60)
    print("【非流式请求 (stream=False)】")
    print("=" * 60)

    t0 = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=MESSAGES,
        temperature=0.7,
        top_p=1.0,
        max_tokens=256,
        stream=False,
    )
    total_s = time.perf_counter() - t0

    choice = response.choices[0]
    finish = choice.finish_reason
    content = choice.message.content or ""

    print(f"总耗时:       {total_s:.3f}s")
    print(f"完成原因:     {finish}")
    print(f"回复长度:     {len(content)} 字符")
    print(f"回复预览:     {content[:80]}...")
    if response.usage:
        print(f"Token 用量:   {json.dumps(dict(prompt_tokens=response.usage.prompt_tokens, completion_tokens=response.usage.completion_tokens, total_tokens=response.usage.total_tokens), ensure_ascii=False)}")

    return total_s


def test_streaming():
    """流式请求：测量首 token 时延和总耗时。"""
    print("\n" + "=" * 60)
    print("【流式请求 (stream=True)】")
    print("=" * 60)

    t0 = time.perf_counter()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=MESSAGES,
        temperature=0.7,
        top_p=1.0,
        max_tokens=256,
        stream=True,
    )

    first_token_s = None
    chunk_count = 0
    content_parts: list[str] = []

    for chunk in stream:
        chunk_count += 1
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        content = getattr(delta, "content", None)
        if content:
            if first_token_s is None:
                first_token_s = time.perf_counter() - t0
            content_parts.append(content)

    total_s = time.perf_counter() - t0
    full_content = "".join(content_parts)

    print(f"首 token 时延: {first_token_s:.3f}s" if first_token_s else "首 token 时延: N/A")
    print(f"总耗时:        {total_s:.3f}s")
    print(f"chunk 总数:    {chunk_count}")
    print(f"content chunk: {len(content_parts)}")
    print(f"回复长度:      {len(full_content)} 字符")
    print(f"回复预览:      {full_content[:80]}...")

    return total_s, first_token_s


def main():
    print("=" * 60)
    print("【非流式 vs 流式 时延对比】")
    print(f"模型: {MODEL}")
    print("=" * 60)

    non_stream_total = test_non_streaming()
    stream_total, first_token = test_streaming()

    print("\n" + "=" * 60)
    print("【对比总结】")
    print("=" * 60)
    print(f"{'指标':<20s} {'非流式':>10s} {'流式':>10s}")
    print("-" * 40)
    print(f"{'首 token 时延':<20s} {'N/A':>10s} {f'{first_token:.3f}s':>10s}")
    print(f"{'总耗时':<20s} {f'{non_stream_total:.3f}s':>10s} {f'{stream_total:.3f}s':>10s}")
    if first_token:
        speedup = non_stream_total / first_token
        print(f"\n💡 流式首 token 比非流式完整响应快约 {speedup:.1f}x")

    print("\n✅ latency_compare 示例运行完成！")


if __name__ == "__main__":
    main()
