"""
Hy3 API 示例 3：流式 vs 非流式对比
====================================

对同一个请求分别使用流式和非流式模式调用，对比：
  - 首 token 延迟（time-to-first-token, TTFT）
  - 总耗时（end-to-end latency）
  - 输出内容一致性

前置条件：
  - 在 https://console.cloud.tencent.com/tokenhub/apikey 创建 API Key
  - 安装 openai: pip install openai

运行方式：
  python streaming_comparison.py
"""

import time
from openai import OpenAI

API_KEY = "sk-你的APIKey"  # TODO: 替换为真实的 API Key

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=API_KEY,
)

# ============================================================
# 测试用的 prompt
# ============================================================
prompt = """请用 Python 实现一个 LRU (Least Recently Used) 缓存，
包含 get 和 put 方法，并解释时间复杂度。"""

print("=" * 60)
print("【流式 vs 非流式 性能对比】")
print("=" * 60)
print(f"\nPrompt: {prompt[:60]}...")

# ============================================================
# 1. 非流式调用
# ============================================================
print("\n" + "-" * 40)
print("1. 非流式调用 (stream=False)")
print("-" * 40)

ns_start = time.time()
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    top_p=1.0,
    stream=False,
    extra_body={"reasoning_effort": "no_think"},
)
non_stream_end = time.time()
non_stream_total = non_stream_end - ns_start

non_stream_content = response.choices[0].message.content
non_stream_usage = response.usage

print(f"总耗时:    {non_stream_total:.2f}s")
print(f"首 token:  等待全部完成后才返回（不可测量）")
print(f"prompt tokens:  {non_stream_usage.prompt_tokens}")
print(f"completion tokens: {non_stream_usage.completion_tokens}")
print(f"总 tokens: {non_stream_usage.total_tokens}")
print(f"输出长度:  {len(non_stream_content)} 字符")

# ============================================================
# 2. 流式调用
# ============================================================
print("\n" + "-" * 40)
print("2. 流式调用 (stream=True)")
print("-" * 40)

s_start = time.time()
first_token_time = None

response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    top_p=1.0,
    stream=True,
    extra_body={"reasoning_effort": "no_think"},
)

stream_full_content = ""
for chunk in response:
    if first_token_time is None:
        first_token_time = time.time()

    delta = chunk.choices[0].delta
    if delta.content:
        stream_full_content += delta.content

    if chunk.choices[0].finish_reason:
        stream_end = time.time()

print(f"首 token 耗时 (TTFT):  {first_token_time - s_start:.2f}s")
print(f"总耗时:               {stream_end - s_start:.2f}s")
print(f"输出长度:             {len(stream_full_content)} 字符")

# ============================================================
# 3. 对比总结
# ============================================================
print("\n" + "=" * 60)
print("【对比总结】")
print("=" * 60)

stream_total = stream_end - s_start

print(f"""
指标                    非流式           流式
-----------------------------------------------
首 token 延迟 (TTFT)     N/A             {first_token_time - s_start:.2f}s
总响应时间               {non_stream_total:.2f}s            {stream_total:.2f}s
输出一致性               —               {'✓ 一致' if non_stream_content == stream_full_content else '⚠ 略有差异'}
内容长度                 {len(non_stream_content)} 字符        {len(stream_full_content)} 字符
""")

print(f"--- 关键结论 ---")
print(f"1. 流式模式下首 token 仅需 {(first_token_time - s_start):.2f}s，"
      f"用户能立即看到模型开始回复")
print(f"2. 内容量较大时，流式总耗时 ({stream_total:.2f}s) "
      f"可能略高于非流式，因逐 chunk 传输有额外开销")
print(f"3. 两种模式的输出内容{'完全一致' if non_stream_content == stream_full_content else '基本一致（差异源于采样随机性）'}")
