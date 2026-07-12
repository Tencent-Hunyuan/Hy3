"""
01_basic_chat.py
单轮与多轮对话示例
"""

import os
from openai import OpenAI


def create_client():
    return OpenAI(
        api_key=os.environ.get("HY3_API_KEY"),
        base_url="https://tokenhub.tencentmaas.com/v1",
    )


def single_turn_chat(client: OpenAI):
    response = client.chat.completions.create(
        model="hy3",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "请用一句话介绍 Hy3。"},
        ],
        temperature=0.7,
        max_tokens=256,
    )

    print("=== 单轮对话 ===")
    print(response.choices[0].message.content)
    print("finish_reason:", response.choices[0].finish_reason)
    print("usage:", response.usage)
    return response


def multi_turn_chat(client: OpenAI):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请用一句话介绍 Hy3。"},
    ]

    first_response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.7,
        max_tokens=256,
    )

    assistant_msg = first_response.choices[0].message
    messages.append({"role": "assistant", "content": assistant_msg.content})
    messages.append({"role": "user", "content": "它适合哪些应用场景？"})

    second_response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        temperature=0.7,
        max_tokens=512,
    )

    print("\n=== 多轮对话 ===")
    print("Assistant 1:", assistant_msg.content)
    print("Assistant 2:", second_response.choices[0].message.content)
    print("finish_reason:", second_response.choices[0].finish_reason)


if __name__ == "__main__":
    client = create_client()
    single_turn_chat(client)
    multi_turn_chat(client)
