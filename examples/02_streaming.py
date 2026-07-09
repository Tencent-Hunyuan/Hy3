"""
Hy3 流式输出示例 (examples/02_streaming.py)

演示如何通过 OpenAI 兼容 API 以流式（streaming）方式调用 Hy3，
逐 token 接收增量输出，并在最后汇总完整文本。

运行前请先通过 vLLM / SGLang 部署 Hy3 服务（默认监听 127.0.0.1:8000）。
可通过环境变量覆盖连接信息：
    HY3_BASE_URL  服务地址（默认 http://127.0.0.1:8000/v1）
    HY3_API_KEY   API Key（本地部署任意值均可，默认 EMPTY）
"""

import os

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

# 一个能够生成多句回答的 prompt
messages = [
    {
        "role": "user",
        "content": (
            "请用中文写一段关于「秋天的银杏林」的短文，"
            "包含颜色、声音和心情的描写，至少三句话。"
        ),
    },
]

print("=== 流式输出（逐 chunk 打印） ===")
stream = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    stream=True,
)

full_text_parts = []
for chunk in stream:
    # 流式响应中每个 chunk 是一个 ChatCompletionChunk
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    content = delta.content
    if content:  # 跳过 None / 空字符串
        # 实时打印增量内容（不换行，模拟打字机效果）
        print(content, end="", flush=True)
        full_text_parts.append(content)

print("\n\n=== 流式结束，汇总完整文本 ===")
full_text = "".join(full_text_parts)
print(full_text)
