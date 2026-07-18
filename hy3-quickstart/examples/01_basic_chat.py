"""
01 · basic chat —— 单轮 / 多轮对话
演示最基础的 chat.completions 调用与多轮上下文。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import get_client, MODEL

client = get_client()

# ── 单轮 ────────────────────────────────────────────────
print("=== 单轮 ===")
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "用一句话解释什么是向量数据库"}],
    temperature=0.7,
    max_tokens=200,
)
msg = resp.choices[0].message
print("content:", msg.content)
print("usage:", resp.usage)
print("model:", resp.model)

# ── 多轮 (带 system + 历史) ─────────────────────────────
print("\n=== 多轮 ===")
resp2 = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": "你是健身教练, 回答简洁"},
        {"role": "user", "content": "增肌每天该吃多少蛋白质?"},
        {"role": "assistant", "content": "一般建议每公斤体重 1.6~2.2 克。"},
        {"role": "user", "content": "那 70 公斤的人大概多少?"},
    ],
    temperature=0.5,
    max_tokens=300,
)
print(resp2.choices[0].message.content)
