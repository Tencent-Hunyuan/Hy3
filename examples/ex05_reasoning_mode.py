"""
ex05_reasoning_mode.py
思考模式开/关对比示例
"""

import os
from openai import OpenAI


def create_client():
    return OpenAI(
        api_key=os.environ.get("HY3_API_KEY"),
        base_url="https://tokenhub.tencentmaas.com/v1",
    )


def ask_with_thinking(client: OpenAI, prompt: str, enabled: bool):
    extra_body = {"thinking": {"type": "enabled" if enabled else "disabled"}}
    response = client.chat.completions.create(
        model="hy3",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=512,
        extra_body=extra_body,
    )

    msg = response.choices[0].message
    mode = "开启思考" if enabled else "关闭思考"
    print(f"=== {mode} ===")

    reasoning = getattr(msg, "reasoning_content", None)
    if reasoning:
        print("【思考过程】")
        print(reasoning)
        print("\n【最终回答】")
    print(msg.content)
    print()


if __name__ == "__main__":
    client = create_client()
    prompt = "9.11 和 9.8 哪个更大？请说明原因。"

    ask_with_thinking(client, prompt, enabled=False)
    ask_with_thinking(client, prompt, enabled=True)
