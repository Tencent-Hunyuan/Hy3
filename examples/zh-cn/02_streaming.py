"""Hy3 示例 02：流式请求和逐 chunk 解析。"""

import os
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120.0)

stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "用 5 个要点解释流式输出适合哪些产品场景。"}],
    temperature=0.7,
    top_p=1.0,
    max_tokens=500,
    stream=True,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

print("assistant: ", end="", flush=True)
full_text = []
chunk_count = 0

for chunk in stream:
    chunk_count += 1
    choice = chunk.choices[0] if chunk.choices else None
    if choice is None:
        continue

    delta = choice.delta
    content = getattr(delta, "content", None)
    if content:
        print(content, end="", flush=True)
        full_text.append(content)

    reasoning_content = getattr(delta, "reasoning_content", None)
    if reasoning_content:
        # 产品 UI 通常不直接展示原始推理内容；只在策略允许时收集或记录。
        pass

    if choice.finish_reason:
        print(f"\n结束原因: {choice.finish_reason}")

print(f"\nchunk 数: {chunk_count}")
print(f"总字符数: {len(''.join(full_text))}")
