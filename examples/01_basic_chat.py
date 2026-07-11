"""
01_basic_chat.py

展示内容：
1. 单轮对话
2. 多轮对话
3. 完整请求与完整 response 解析

运行方式：
    pip install -r examples/requirements.txt
    Copy-Item .env.example .env
    python examples/01_basic_chat.py

配置：编辑仓库根目录的 .env，设置 API_PROVIDER=hy3 或 API_PROVIDER=hunyuan。

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

from typing import Iterable

from openai import OpenAI

from config import MODEL, build_client, reasoning_extra_body


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
        extra_body=reasoning_extra_body("no_think"),
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
        extra_body=reasoning_extra_body("low"),
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
