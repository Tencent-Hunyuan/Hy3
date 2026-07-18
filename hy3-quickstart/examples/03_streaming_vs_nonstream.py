"""
03 · non-streaming vs streaming —— 首 token 时延 / 总耗时对比
演示流式 (低首 token 延迟) 与非流式 (整段返回) 的耗时差异。
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import get_client, MODEL

client = get_client()
Q = "用 80 字介绍腾讯混元 Hy3 模型的特点"

# ── 非流式 ──────────────────────────────────────────────
t0 = time.perf_counter()
r1 = client.chat.completions.create(
    model=MODEL, messages=[{"role": "user", "content": Q}], max_tokens=300
)
non_total = time.perf_counter() - t0
print("=== 非流式 ===")
print(f"  首 token ≈ {non_total*1000:.0f} ms (整段才返回)")
print(f"  总耗时     = {non_total*1000:.0f} ms")
print(f"  字数       = {len(r1.choices[0].message.content)}")

# ── 流式 (测首 token) ───────────────────────────────────
print("\n=== 流式 ===")
t0 = time.perf_counter()
stream = client.chat.completions.create(
    model=MODEL, messages=[{"role": "user", "content": Q}], stream=True, max_tokens=300
)
first_ttft = None
total_chars = 0
for chunk in stream:
    if not chunk.choices:
        continue
    content = chunk.choices[0].delta.content or ""
    if content:
        if first_ttft is None:
            first_ttft = time.perf_counter() - t0
        total_chars += len(content)
stream_total = time.perf_counter() - t0
print(f"  首 token (TTFT) = {first_ttft*1000:.0f} ms")
print(f"  总耗时           = {stream_total*1000:.0f} ms")
print(f"  字数             = {total_chars}")
