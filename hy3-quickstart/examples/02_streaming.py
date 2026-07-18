"""
02 · streaming —— 流式请求 + 逐 chunk 解析
演示 SSE 流式输出, 并解析每个 chunk 的 delta (含思考内容 reasoning_content)。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import get_client, MODEL

client = get_client()

print("=== 流式 (逐 chunk) ===")
stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "写一首关于代码的俳句, 三行"}],
    stream=True,
    max_tokens=300,
)

full_content = ""
full_reasoning = ""
chunk_count = 0
for chunk in stream:
    chunk_count += 1
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta

    # 思考过程 (Hy3 交错式思考, 字段为 reasoning_content)
    reasoning = getattr(delta, "reasoning_content", None)
    if reasoning:
        full_reasoning += reasoning
        print(f"\r[think] {reasoning}", end="", flush=True)

    # 正文
    content = delta.content or ""
    if content:
        full_content += content
        print(content, end="", flush=True)

print("\n")
print(f"--- 共 {chunk_count} 个 chunk ---")
print(f"reasoning 长度: {len(full_reasoning)} 字")
print(f"content 长度: {len(full_content)} 字")
print(f"拼接结果:\n{full_content}")
