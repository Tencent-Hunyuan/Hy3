import os
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

def main():
    # 真正的请求
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Write a short checklist for testing a REST API."}
        ],
        temperature=0.9,
        top_p=1.0,
        max_tokens=512,
        stream=True,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )

    print("Assistant:", end="", flush=True)
    # 流式解析的核心
    '''
    非流式结构：完整的回答
    response
    └── choices[0]
        └── message
            └── content = 完整回答
    流式的结构：消息增量
    chunk
    └── choices[0]
        └── delta
            └── content = 当前新增文本
    '''
    for chunk in stream:
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta
        if delta and delta.content:
            print(delta.content, end="", flush=True)
    print()


if __name__ == "__main__":
    main()