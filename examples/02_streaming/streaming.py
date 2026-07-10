"""
Hy3 API 示例 2：Streaming（流式请求）
======================================

演示流式模式下逐 token 接收响应，适用于实时对话场景。

前置条件：
  - 在 https://console.cloud.tencent.com/tokenhub/apikey 创建 API Key
  - 安装 openai: pip install openai

运行方式：
  python streaming.py
"""

import time
from openai import OpenAI

API_KEY = "sk-你的APIKey"  # TODO: 替换为真实的 API Key

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=API_KEY,
)

prompt = "请写一段关于人工智能未来发展的短文，大约200字左右。"

print(f"User: {prompt}")
print("\nAssistant: ", end="", flush=True)

# ============================================================
# 1. 流式请求 —— 设置 stream=True
# ============================================================
start_time = time.time()
first_token_time = None

response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9,
    top_p=1.0,
    stream=True,  # 开启流式模式
    extra_body={"reasoning_effort": "no_think"},
)

full_content = ""
for chunk in response:
    # 记录首 token 到达时间
    if first_token_time is None:
        first_token_time = time.time()
        print(f"\n--- 首 token 耗时: {first_token_time - start_time:.2f}s ---\n")

    delta = chunk.choices[0].delta
    content = delta.content or ""

    if content:
        full_content += content
        print(content, end="", flush=True)

    # 检查结束原因
    if chunk.choices[0].finish_reason:
        finish_reason = chunk.choices[0].finish_reason
        end_time = time.time()

print()  # 换行

# ============================================================
# 2. 统计信息
# ============================================================
print(f"\n--- 流式请求统计 ---")
print(f"首 token 耗时:   {first_token_time - start_time:.2f}s")
print(f"总耗时:          {end_time - start_time:.2f}s")
print(f"生成 token 数:   ~{len(full_content)} 字符")
print(f"结束原因:        {finish_reason}")

# ============================================================
# 3. 流式 chunk 结构解析
# ============================================================
print("\n--- 流式 chunk 结构示例 ---")

# 重新发送一次请求，只取前几个 chunk 做演示
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "用三个词回答：今天天气怎么样？"}],
    temperature=0.7,
    top_p=1.0,
    stream=True,
    extra_body={"reasoning_effort": "no_think"},
)

for i, chunk in enumerate(response):
    if i >= 4:  # 只展示前 4 个 chunk
        break
    print(f"\nChunk {i}:")
    print(f"  id:             {chunk.id}")
    print(f"  object:         {chunk.object}")
    print(f"  choices[0].delta:     role={chunk.choices[0].delta.role}, content={repr(chunk.choices[0].delta.content)}")
    print(f"  choices[0].finish_reason: {chunk.choices[0].finish_reason}")
