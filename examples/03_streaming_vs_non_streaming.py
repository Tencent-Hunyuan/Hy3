"""
Hy3 API - 流式 vs 非流式对比 / Streaming vs Non-Streaming Comparison
量化首 token 时延（TTFT）和总耗时
"""

import time
from openai import OpenAI

# ============================================================
# 配置 / Configuration
# ============================================================
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

PROMPT = "请详细介绍Python中的装饰器模式，包括使用场景和代码示例。"


# ============================================================
# 非流式请求 / Non-Streaming Request
# ============================================================
def run_non_streaming():
    """非流式请求：等待完整响应后一次性返回"""
    print("=" * 60)
    print("非流式请求 / Non-Streaming Request")
    print("=" * 60)

    t_start = time.time()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        stream=False,
    )

    total_time = time.time() - t_start
    content = response.choices[0].message.content

    print(f"\n回复（前200字符）：{content[:200]}...")
    print(f"\n首 token 时延：{total_time:.2f}s（与非流式总耗时相同）")
    print(f"总耗时：{total_time:.2f}s")
    print(f"内容长度：{len(content)} 字符")

    return total_time, total_time, len(content)


# ============================================================
# 流式请求 / Streaming Request
# ============================================================
def run_streaming():
    """流式请求：逐 chunk 接收，记录首 token 时延"""
    print("\n" + "=" * 60)
    print("流式请求 / Streaming Request")
    print("=" * 60)

    t_start = time.time()
    first_token_time = None
    full_content = ""
    chunk_count = 0

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        temperature=0.9,
        top_p=1.0,
        stream=True,
    )

    print("\n回复（前200字符）：", end="")

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            # 记录首 token 到达时间
            if first_token_time is None:
                first_token_time = time.time() - t_start

            full_content += delta.content
            chunk_count += 1

            # 仅打印前200字符
            if len(full_content) <= 200:
                print(delta.content, end="", flush=True)

    total_time = time.time() - t_start

    if len(full_content) > 200:
        print("...", end="")

    print(f"\n\n首 token 时延：{first_token_time:.2f}s")
    print(f"总耗时：{total_time:.2f}s")
    print(f"内容长度：{len(full_content)} 字符")
    print(f"Chunk 数量：{chunk_count}")

    return first_token_time, total_time, len(full_content)


# ============================================================
# 对比总结 / Comparison Summary
# ============================================================
def compare(ttft_non, total_non, len_non, ttft_stream, total_stream, len_stream):
    """打印对比表格"""
    print("\n" + "=" * 60)
    print("对比总结 / Comparison Summary")
    print("=" * 60)

    print(f"\n{'指标':<20} {'非流式':>14} {'流式':>14} {'差异':>14}")
    print("-" * 66)
    print(f"{'首 token 时延 (TTFT)':<20} {ttft_non:>12.2f}s {ttft_stream:>12.2f}s "
          f"{ttft_non - ttft_stream:>+12.2f}s")
    print(f"{'总耗时':<20} {total_non:>12.2f}s {total_stream:>12.2f}s "
          f"{total_stream - total_non:>+12.2f}s")
    print(f"{'内容长度':<20} {len_non:>12} {len_stream:>12}")

    speedup = ttft_non / ttft_stream if ttft_stream > 0 else float("inf")
    print(f"\n流式首 token 加速比：{speedup:.1f}x")
    print("\n结论：流式模式首 token 到达更快，适合实时交互；")
    print("      非流式总耗时略短，适合后端批处理场景。")


# ============================================================
# 运行示例
# ============================================================
if __name__ == "__main__":
    ttft_non, total_non, len_non = run_non_streaming()
    ttft_stream, total_stream, len_stream = run_streaming()
    compare(ttft_non, total_non, len_non, ttft_stream, total_stream, len_stream)
