"""Hy3 示例 01：单轮 / 多轮对话。

通过 OpenAI 兼容 API 调用本地部署的 Hy3 模型，演示：
1. 单轮对话：发送一条用户消息并打印回复。
2. 多轮对话：携带 system / user / assistant / user 历史记录再次调用，
   展示上下文如何被带入下一轮。

连接信息通过环境变量读取，未设置时使用默认本地服务地址。
"""

import os

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"


def chat(messages):
    """统一封装一次对话请求，固定使用推荐参数并关闭思考。"""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )


def single_turn():
    """单轮对话：仅包含一条用户消息。"""
    print("=" * 60)
    print("【单轮对话】")
    print("=" * 60)

    messages = [
        {"role": "user", "content": "用一句话介绍腾讯混元 Hy3 模型。"},
    ]
    response = chat(messages)

    print(f"用户: {messages[0]['content']}")
    print(f"助手: {response.choices[0].message.content}")
    print()


def multi_turn():
    """多轮对话：把上一轮的 assistant 回复追加进 messages，再次调用。"""
    print("=" * 60)
    print("【多轮对话】")
    print("=" * 60)

    messages = [
        {"role": "system", "content": "你是一个简洁友好的中文助手。"},
        {"role": "user", "content": "Hy3 的上下文长度是多少？"},
        {"role": "assistant", "content": "Hy3 的上下文长度为 256K tokens。"},
        {"role": "user", "content": "那它的激活参数量是多少？"},
    ]
    response = chat(messages)

    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    print(f"assistant: {response.choices[0].message.content}")
    print()


if __name__ == "__main__":
    single_turn()
    multi_turn()
