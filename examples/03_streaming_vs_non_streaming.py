"""
03_streaming_vs_non_streaming.py

展示内容：
1. non-streaming 总耗时
2. streaming 首 token 时延
3. streaming 总耗时
4. 两种模式的 response 解析方式

运行方式：
    pip install -r examples/requirements.txt
    Copy-Item .env.example .env
    python examples/03_streaming_vs_non_streaming.py

配置：编辑仓库根目录的 .env，设置 API_PROVIDER=hy3 或 API_PROVIDER=hunyuan。

示例输出：
    Non-streaming total time: 8.42s
    Streaming first token latency: 1.31s
    Streaming total time: 8.76s
"""

from __future__ import annotations

import time

from openai import OpenAI


from config import MODEL, build_client, reasoning_extra_body
PROMPT = "请写一段 200 字左右的说明，介绍 Hy3 在聊天、代码和工具调用场景中的典型用法。"


def run_non_streaming(client: OpenAI) -> tuple[str, float]:
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        top_p=1.0,
        max_tokens=512,
        extra_body=reasoning_extra_body("no_think"),
    )
    total_time = time.perf_counter() - start
    return response.choices[0].message.content or "", total_time


def run_streaming(client: OpenAI) -> tuple[str, float | None, float]:
    start = time.perf_counter()
    first_token_time = None
    parts: list[str] = []

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.7,
        top_p=1.0,
        max_tokens=512,
        stream=True,
        extra_body=reasoning_extra_body("no_think"),
    )

    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            if first_token_time is None:
                first_token_time = time.perf_counter() - start
            parts.append(delta)

    total_time = time.perf_counter() - start
    return "".join(parts), first_token_time, total_time


def main() -> None:
    client = build_client()

    non_stream_text, non_stream_total = run_non_streaming(client)
    stream_text, first_token_latency, stream_total = run_streaming(client)

    print(f"Non-streaming total time: {non_stream_total:.2f}s")
    if first_token_latency is None:
        print("Streaming first token latency: <no token received>")
    else:
        print(f"Streaming first token latency: {first_token_latency:.2f}s")
    print(f"Streaming total time: {stream_total:.2f}s")

    print("\n=== Non-streaming preview ===")
    print(non_stream_text[:200])

    print("\n=== Streaming preview ===")
    print(stream_text[:200])


if __name__ == "__main__":
    main()
