"""
Example 3: Non-streaming vs Streaming — TTFT & total time comparison

Prerequisites:
  - Hy3 server running on port 8000
  - pip install openai
"""

import time
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

PROMPT = "请用 300 字左右详细解释什么是 Transformer 架构，包括自注意力机制的原理。"

# Non-streaming
print("=" * 60)
print("Non-streaming 模式")
print("=" * 60)

start = time.perf_counter()
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": PROMPT}],
    temperature=0.7,
    max_tokens=512,
    stream=False,
)

content = response.choices[0].message.content
total_time = time.perf_counter() - start
token_count = response.usage.completion_tokens if response.usage else len(content)

print(f"首 token 时延 (TTFT): {total_time:.2f}s  (非流式下 ≈ 总耗时)")
print(f"总耗时:             {total_time:.2f}s")
print(f"生成 tokens:         {token_count}")
print(f"平均速度:            {token_count / total_time:.1f} tokens/s")
print(f"前 100 字符预览:    {content[:100]}...")

# Streaming
print("\n" + "=" * 60)
print("Streaming 模式")
print("=" * 60)

start = time.perf_counter()
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": PROMPT}],
    temperature=0.7,
    max_tokens=512,
    stream=True,
)

first_chunk = True
full_content = ""
chunk_count = 0
for chunk in response:
    if first_chunk:
        ttft = time.perf_counter() - start
        first_chunk = False
    delta = chunk.choices[0].delta
    if delta.content:
        full_content += delta.content
        chunk_count += 1

total_time_stream = time.perf_counter() - start
token_count_stream = len(full_content.split())

print(f"首 token 时延 (TTFT): {ttft:.2f}s")
print(f"总耗时:             {total_time_stream:.2f}s")
print(f"chunk 数量:          {chunk_count}")
print(f"预估 tokens:         {token_count_stream}")
print(f"平均速度:            {token_count_stream / total_time_stream:.1f} tokens/s")
print(f"前 100 字符预览:    {full_content[:100]}...")

# 对比总结
print("\n" + "=" * 60)
print("对比总结")
print("=" * 60)
print(f"{'指标':<25} {'Non-streaming':<20} {'Streaming':<20}")
print(f"{'—'*25:<25} {'—'*20:<20} {'—'*20:<20}")
print(f"{'首 token 时延 (TTFT)':<25} {total_time:<20.2f} {ttft:<20.2f}")
print(f"{'总耗时':<25} {total_time:<20.2f} {total_time_stream:<20.2f}")
print(f"{'用户体验':<25} {'等待全部生成':<20} {'实时输出':<20}")
print(f"{'适用场景':<25} {'简单问答/分析':<20} {'聊天/实时展示':<20}")
