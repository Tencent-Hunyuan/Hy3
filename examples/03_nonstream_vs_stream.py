"""
Hy3 非流式 vs 流式延迟对比示例 (examples/03_nonstream_vs_stream.py)

对同一个 prompt 分别以非流式和流式方式调用 Hy3，
使用 time.perf_counter() 测量：
    - 非流式：总耗时（等待完整生成返回）
    - 流式：首 token 延迟（TTFT，首个非空 delta.content 到达时间）与总耗时

运行前请先通过 vLLM / SGLang 部署 Hy3 服务（默认监听 127.0.0.1:8000）。
可通过环境变量覆盖连接信息：
    HY3_BASE_URL  服务地址（默认 http://127.0.0.1:8000/v1）
    HY3_API_KEY   API Key（本地部署任意值均可，默认 EMPTY）
"""

import os
import time

from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

# 固定的对比 prompt
messages = [
    {
        "role": "user",
        "content": (
            "请用中文简要介绍混合专家模型（MoE）的工作原理，"
            "并举一个生活中的类比，回答约 150 字。"
        ),
    },
]

common_kwargs = dict(
    model="hy3",
    messages=messages,
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

# ---------- 非流式 ----------
print("=== 非流式调用 ===")
t0 = time.perf_counter()
response = client.chat.completions.create(**common_kwargs, stream=False)
t1 = time.perf_counter()
nonstream_total = t1 - t0
nonstream_text = response.choices[0].message.content
print(f"响应内容:\n{nonstream_text}")
print(f"\n非流式总耗时: {nonstream_total:.3f} s\n")

# ---------- 流式 ----------
print("=== 流式调用 ===")
t0 = time.perf_counter()
stream = client.chat.completions.create(**common_kwargs, stream=True)
ttft = None
parts = []
for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    content = delta.content
    if content:  # 首个非空 token
        if ttft is None:
            ttft = time.perf_counter() - t0
        parts.append(content)
t1 = time.perf_counter()
stream_total = t1 - t0
stream_text = "".join(parts)
print(f"响应内容:\n{stream_text}")
print(f"\n流式首 token 延迟 (TTFT): {ttft:.3f} s")
print(f"流式总耗时: {stream_total:.3f} s\n")

# ---------- 对比汇总 ----------
print("=== 对比汇总 ===")
print(f"非流式总耗时:           {nonstream_total:.3f} s")
print(f"流式  TTFT:             {ttft:.3f} s")
print(f"流式  总耗时:           {stream_total:.3f} s")
if ttft is not None:
    print(f"TTFT / 非流式总耗时:    {ttft / nonstream_total:.1%}")
