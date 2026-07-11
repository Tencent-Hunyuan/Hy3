"""
02_streaming.py

展示内容：
1. stream=True 的完整请求
2. 逐 chunk 解析 response
3. 流式输出的示例打印方式

运行方式：
    pip install -r examples/requirements.txt
    Copy-Item .env.example .env
    python examples/02_streaming.py

配置：编辑仓库根目录的 .env，设置 API_PROVIDER=hy3 或 API_PROVIDER=hunyuan。

示例输出：
    Starting stream...
    Hy3 是一个...
    [stream finished]
"""

from __future__ import annotations

from config import MODEL, build_client, reasoning_extra_body


def main() -> None:
    client = build_client()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "请用三句话介绍 Hy3，并说明它适合什么开发场景。"}
        ],
        temperature=0.7,
        top_p=1.0,
        max_tokens=512,
        stream=True,
        extra_body=reasoning_extra_body("no_think"),
    )

    print("Starting stream...\n")
    collected_text: list[str] = []

    for chunk in response:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            collected_text.append(delta.content)
            print(delta.content, end="", flush=True)

    print("\n\n[stream finished]")
    print(f"Collected {len(''.join(collected_text))} characters.")


if __name__ == "__main__":
    main()
