"""Hy3 示例 01：基础聊天，包含单轮和多轮调用。"""

import os
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=60.0)


def print_response(title, response):
    message = response.choices[0].message
    print(f"\n=== {title} ===")
    print("assistant:", message.content)
    print("结束原因:", response.choices[0].finish_reason)
    print("用量:", response.usage)


single_turn = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "请用三句话介绍 Hy3 适合什么开发场景。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=300,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print_response("单轮", single_turn)

messages = [
    {"role": "system", "content": "你是一个简洁、准确的开发者助手。"},
    {"role": "user", "content": "给我一个 Python 列表去重但保持顺序的函数。"},
]
first = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.3,
    max_tokens=400,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print_response("多轮 / 第 1 轮", first)

messages.append({"role": "assistant", "content": first.choices[0].message.content})
messages.append({"role": "user", "content": "再补充一个带类型注解和简单测试的版本。"})
second = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    temperature=0.3,
    max_tokens=600,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print_response("多轮 / 第 2 轮", second)
