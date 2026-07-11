"""
02_streaming.py

展示内容：
1. stream=True 的完整请求
2. 逐 chunk 解析 response
3. 流式输出的示例打印方式

运行方式：
    pip install openai
    python examples/02_streaming.py

示例输出：
    Starting stream...
    Hy3 是一个...
    [stream finished]
"""

from __future__ import annotations

import os

from openai import OpenAI


BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")


def main() -> None:
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "请用三句话介绍 Hy3，并说明它适合什么开发场景。"}
        ],
        temperature=0.7,
        top_p=1.0,
        max_tokens=512,
        stream=True,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )

    print("Starting stream...\n")
    collected_text: list[str] = []

    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            collected_text.append(delta.content)
            print(delta.content, end="", flush=True)

    print("\n\n[stream finished]")
    print(f"Collected {len(''.join(collected_text))} characters.")


if __name__ == "__main__":
    main()
