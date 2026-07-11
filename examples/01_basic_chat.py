"""
01_basic_chat.py

展示内容：
1. 单轮对话
2. 多轮对话
3. 完整请求与完整 response 解析

运行方式：
    pip install openai
    python examples/01_basic_chat.py

环境变量：
    HY3_BASE_URL  默认 http://127.0.0.1:8000/v1
    HY3_API_KEY   默认 EMPTY
    HY3_MODEL     默认 hy3

示例输出：
    === Single-turn chat ===
    Response ID: chatcmpl-xxx
    Model: hy3
    Content:
    Hy3 是腾讯混元团队推出的大模型...

    === Multi-turn chat ===
    Content:
    适合。Hy3 在代码、工具调用和推理任务上...
"""

from __future__ import annotations

import os
from typing import Iterable

from openai import OpenAI


BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")


def build_client() -> OpenAI:
    return OpenAI(base_url=BASE_URL, api_key=API_KEY)


def print_usage(usage: object) -> None:
    if not usage:
        print("Usage: <not returned by server>")
        return
    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)
    print(
        f"Usage: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}"
    )


def print_messages(title: str, messages: Iterable[dict[str, str]]) -> None:
    print(title)
    for message in messages:
        print(f"- {message['role']}: {message['content']}")


def run_single_turn(client: OpenAI) -> None:
    messages = [
        {"role": "user", "content": "介绍一下 Hy3"},
    ]
    print("\n=== Single-turn chat ===")
    print_messages("Request messages:", messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )

    message = response.choices[0].message
    print(f"Response ID: {response.id}")
    print(f"Model: {response.model}")
    print("Content:")
    print(message.content or "")
    print_usage(response.usage)


def run_multi_turn(client: OpenAI) -> None:
    messages = [
        {"role": "user", "content": "介绍一下 Hy3"},
        {"role": "assistant", "content": "Hy3 是一个支持通用问答、代码和推理任务的大模型。"},
        {"role": "user", "content": "它适合做代码任务吗？"},
    ]
    print("\n=== Multi-turn chat ===")
    print_messages("Request messages:", messages)

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.6,
        top_p=1.0,
        max_tokens=512,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "low"}},
    )

    message = response.choices[0].message
    print("Content:")
    print(message.content or "")
    print_usage(response.usage)


def main() -> None:
    client = build_client()
    run_single_turn(client)
    run_multi_turn(client)


if __name__ == "__main__":
    main()
