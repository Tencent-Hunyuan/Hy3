"""示例 02：流式输出（逐 chunk 解析）

运行:
    python 02_streaming.py
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=int(os.environ.get("HY3_TIMEOUT_SECONDS", "60")),
)
MODEL = os.environ.get("HY3_MODEL", "hy3")
REASONING = {"chat_template_kwargs": {"reasoning_effort": "no_think"}}


def main() -> None:
    print("=== 流式输出（逐字打印）===\n")

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "用三句话介绍腾讯混元大模型。"}],
        temperature=0.9,
        max_tokens=256,
        stream=True,                                  #开启流式输出
        stream_options={"include_usage": True},       #返回chunk尾块
        extra_body=REASONING,
    )

    full_text = ""      # 拼接完整回答
    prompt_tokens = completion_tokens = total_tokens = None

    for chunk in stream:
        # usage 尾块：choices 为空，只带 usage（开启 include_usage 后才有）
        if not chunk.choices:
            if chunk.usage is not None:
                prompt_tokens = chunk.usage.prompt_tokens
                completion_tokens = chunk.usage.completion_tokens
                total_tokens = chunk.usage.total_tokens
            continue

        # 每个内容 chunk 的结构:
        #   chunk.choices[0].delta.content
        #   chunk.choices[0].finish_reason
        delta = chunk.choices[0].delta

        # 内容片段：直接打印
        if delta.content:
            print(delta.content, end="", flush=True)
            full_text += delta.content

        # 部分服务也在最后一个内容 chunk 附带 usage
        if chunk.usage is not None:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens
            total_tokens = chunk.usage.total_tokens

        # 结束原因（finish_reason）
        if chunk.choices[0].finish_reason:
            print(f"\n\n[finish_reason={chunk.choices[0].finish_reason}]")

    print("\n--- 拼接后的完整回答 ---")
    print(full_text)
    if total_tokens is not None:
        print(f"Token 用量: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")


if __name__ == "__main__":
    main()
