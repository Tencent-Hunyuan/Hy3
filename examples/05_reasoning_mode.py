"""
05_reasoning_mode.py

展示内容：
1. reasoning_effort=no_think 与 high 的调用方式
2. 对比响应时间和最终答案长度
3. 如果服务端返回 reasoning_content，则打印；如果没有，则明确说明

运行方式：
    pip install openai
    python examples/05_reasoning_mode.py

示例输出：
    [no_think] elapsed=3.20s chars=182
    [high] elapsed=6.84s chars=356
    reasoning_content: <not exposed by server>
"""

from __future__ import annotations

import os
import time

from openai import OpenAI


BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")
PROMPT = "请设计一个 Python 函数，用于合并两个有序数组，并解释时间复杂度与边界情况。"


def run_case(client: OpenAI, reasoning_effort: str) -> None:
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.2,
        top_p=1.0,
        max_tokens=768,
        extra_body={
            "chat_template_kwargs": {
                "reasoning_effort": reasoning_effort,
            }
        },
    )
    elapsed = time.perf_counter() - start

    message = response.choices[0].message
    content = message.content or ""
    reasoning_content = getattr(message, "reasoning_content", None)

    print(f"\n[{reasoning_effort}] elapsed={elapsed:.2f}s chars={len(content)}")
    if reasoning_content:
        print("reasoning_content:")
        print(reasoning_content)
    else:
        print("reasoning_content: <not exposed by server>")

    print("final answer preview:")
    print(content[:400])


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    run_case(client, "no_think")
    run_case(client, "high")


if __name__ == "__main__":
    main()
