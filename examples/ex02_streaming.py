"""
ex02_streaming.py
流式请求与逐 chunk 解析示例
"""

import os
from openai import OpenAI


def stream_chat(client: OpenAI):
    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "请写一首关于人工智能的短诗。"},
        ],
        temperature=0.8,
        max_tokens=512,
        stream=True,
    )

    print("=== 流式输出 ===")
    full_content = ""
    reasoning_content = ""

    for chunk in response:
        choice = chunk.choices[0]
        delta = choice.delta

        if delta:
            if getattr(delta, "reasoning_content", None):
                reasoning_content += delta.reasoning_content

            if delta.content:
                full_content += delta.content
                print(delta.content, end="", flush=True)

        if choice.finish_reason:
            print(f"\n[finish_reason: {choice.finish_reason}]")

    print("\n=== 拼接后的完整内容 ===")
    print(full_content)

    if reasoning_content:
        print("\n=== 推理过程 ===")
        print(reasoning_content)


if __name__ == "__main__":
    client = OpenAI(
        api_key=os.environ.get("HY3_API_KEY"),
        base_url="https://tokenhub.tencentmaas.com/v1",
    )
    stream_chat(client)
