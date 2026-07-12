"""
03_latency_comparison.py
非流式与流式的首 token 时延 / 总耗时对比
"""

import os
import time
from openai import OpenAI


def create_client():
    return OpenAI(
        api_key=os.environ.get("HY3_API_KEY"),
        base_url="https://tokenhub.tencentmaas.com/v1",
    )


PROMPT = "请用 300 字左右解释机器学习中的梯度下降算法。"


def measure_non_streaming(client: OpenAI):
    start = time.perf_counter()
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        max_tokens=512,
        stream=False,
    )
    end = time.perf_counter()

    content = response.choices[0].message.content
    print("=== 非流式 ===")
    print(f"首 token 时延: {end - start:.3f}s (非流式需等全部生成完才能拿到结果)")
    print(f"总耗时: {end - start:.3f}s")
    print(f"输出长度: {len(content)} 字符")
    print(content[:200] + "...")
    return end - start


def measure_streaming(client: OpenAI):
    start = time.perf_counter()
    first_token_time = None
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        max_tokens=512,
        stream=True,
    )

    full_content = ""
    for chunk in response:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            if first_token_time is None:
                first_token_time = time.perf_counter()
            full_content += delta.content

    end = time.perf_counter()

    print("\n=== 流式 ===")
    ttft = first_token_time - start if first_token_time else end - start
    print(f"首 token 时延 (TTFT): {ttft:.3f}s")
    print(f"总耗时: {end - start:.3f}s")
    print(f"输出长度: {len(full_content)} 字符")
    print(full_content[:200] + "...")
    return end - start


if __name__ == "__main__":
    client = create_client()
    non_stream_total = measure_non_streaming(client)
    stream_total = measure_streaming(client)
    print(f"\n对比：非流式总耗时 {non_stream_total:.3f}s，流式总耗时 {stream_total:.3f}s")
