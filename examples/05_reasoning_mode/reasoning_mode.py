"""
Hy3 API 示例 5：推理模式对比（快思考 vs 慢思考）
=================================================

对比 Hy3 的三种推理模式：
  - no_think: 直接回答，适合日常对话
  - low:      轻量推理，适合中等复杂度任务
  - high:     深度推理，适合复杂数学/逻辑/代码

前置条件：
  - 在 https://console.cloud.tencent.com/tokenhub/apikey 创建 API Key
  - 安装 openai: pip install openai

运行方式：
  python reasoning_mode.py
"""

import time
from openai import OpenAI

API_KEY = "sk-你的APIKey"  # TODO: 替换为真实的 API Key

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=API_KEY,
)

# ============================================================
# 测试 prompt —— 需要一定推理能力的逻辑题
# ============================================================
prompt = """有三个盒子：一个盒子只装苹果，一个盒子只装橘子，一个盒子既装苹果又装橘子。
三个盒子的标签都贴错了。你只能从一个盒子里拿出一个水果来看，然后判断出每个盒子里装的是什么。
请问最少需要拿几次？为什么？"""

print("=" * 60)
print("【推理模式对比】")
print("=" * 60)
print(f"\nPrompt: {prompt[:80]}...\n")

# ============================================================
# 模式 1：no_think（直接回答/快思考）
# ============================================================
print("-" * 60)
print("模式 1: reasoning_effort = 'no_think'（快思考）")
print("-" * 60)

start = time.time()
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    top_p=1.0,
    extra_body={"reasoning_effort": "no_think"},
)
elapsed = time.time() - start

message = response.choices[0].message
print(f"耗时: {elapsed:.2f}s")
print(f"包含 reasoning_content: {'✅ 有' if getattr(message, 'reasoning_content', None) else '❌ 无'}")
print(f"\n回答:\n{message.content[:300]}")
print()

# ============================================================
# 模式 2：low（轻量推理）
# ============================================================
print("-" * 60)
print("模式 2: reasoning_effort = 'low'（轻量推理）")
print("-" * 60)

start = time.time()
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    top_p=1.0,
    extra_body={"reasoning_effort": "low"},
)
elapsed = time.time() - start

message = response.choices[0].message
print(f"耗时: {elapsed:.2f}s")
print(f"包含 reasoning_content: {'✅ 有' if getattr(message, 'reasoning_content', None) else '❌ 无'}")
if getattr(message, 'reasoning_content', None):
    print(f"\n思考过程片段:\n{message.reasoning_content[:300]}...\n")
print(f"最终回答:\n{message.content[:300]}")
print()

# ============================================================
# 模式 3：high（深度推理/慢思考）
# ============================================================
print("-" * 60)
print("模式 3: reasoning_effort = 'high'（慢思考）")
print("-" * 60)

start = time.time()
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7,
    top_p=1.0,
    extra_body={"reasoning_effort": "high"},
)
elapsed = time.time() - start

message = response.choices[0].message
print(f"耗时: {elapsed:.2f}s")
print(f"包含 reasoning_content: {'✅ 有' if getattr(message, 'reasoning_content', None) else '❌ 无'}")
if getattr(message, 'reasoning_content', None):
    print(f"\n思考过程片段:\n{message.reasoning_content[:500]}...\n")
print(f"最终回答:\n{message.content[:300]}")
print()

# ============================================================
# 对比总结
# ============================================================
print("=" * 60)
print("【三种模式对比总结】")
print("=" * 60)
print("""
┌──────────────┬──────────────┬──────────────────┬──────────────────────┐
│   模式       │  推理过程     │  响应速度          │  适用场景             │
├──────────────┼──────────────┼──────────────────┼──────────────────────┤
│ no_think     │  无推理过程  │  最快              │  日常对话、简单问答    │
│ low          │  简短推理    │  较快              │  中等复杂度任务        │
│ high         │  详细推理    │  较慢（但更准确）   │  数学/编码/逻辑推理    │
└──────────────┴──────────────┴──────────────────┴──────────────────────┘

选择建议：
  - 日常对话 → no_think（默认，无需额外设置）
  - 需要一些推理但不想太慢 → low
  - 复杂推理、数学、代码 → high（推荐使用 reasoning_content 提取思考过程）
""")
