"""
Example 5: Reasoning Mode — compare no_think / low / high

Hy3 supports three reasoning modes:
  - no_think: direct response (default)
  - low:      fast reasoning, short CoT
  - high:     deep reasoning, full CoT

Set via extra_body.chat_template_kwargs.reasoning_effort.

Prerequisites:
  - Hy3 server running on port 8000
  - vLLM: --reasoning-parser hy_v3 / SGLang: --reasoning-parser hunyuan
  - pip install openai
"""

from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

question = "一个水池有一个进水管和一个出水管。单独开进水管 6 小时可以注满水池，单独开出水管 8 小时可以排空水池。如果同时打开两个水管，需要多少小时才能将水池注满？"

# 1. no_think
print("=" * 60)
print("1. reasoning_effort = no_think（直接回答）")
print("=" * 60)

response_no_think = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": question}],
    temperature=0.7,
    max_tokens=1024,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)
reply = response_no_think.choices[0].message.content
print(f"回答:\n{reply}\n")

# 2. low
print("=" * 60)
print("2. reasoning_effort = low（快速思考）")
print("=" * 60)

response_low = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": question}],
    temperature=0.7,
    max_tokens=1024,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "low"}
    },
)
reply = response_low.choices[0].message.content
print(f"回答:\n{reply}\n")

# 3. high
print("=" * 60)
print("3. reasoning_effort = high（深度思考）")
print("=" * 60)

response_high = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": question}],
    temperature=0.7,
    max_tokens=1024,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "high"}
    },
)
reply = response_high.choices[0].message.content
print(f"回答:\n{reply}\n")

print("=" * 60)
print("模式对比")
print("=" * 60)
print(f"{'模式':<15} {'回答长度':<15} {'特点':<30}")
print(f"{'—'*15:<15} {'—'*15:<15} {'—'*30:<30}")
print(f"{'no_think':<15} {len(response_no_think.choices[0].message.content):<15} {'直接输出，无思考过程':<30}")
print(f"{'low':<15} {len(response_low.choices[0].message.content):<15} {'简短推理链':<30}")
print(f"{'high':<15} {len(response_high.choices[0].message.content):<15} {'完整思维链':<30}")
