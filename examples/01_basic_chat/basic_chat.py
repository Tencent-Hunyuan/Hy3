"""
Hy3 API 示例 1：基本聊天 —— 单轮对话与多轮对话
=============================================

通过腾讯云 TokenHub 调用 Hy3 API。

前置条件：
  - 在 https://console.cloud.tencent.com/tokenhub/apikey 创建 API Key
  - 安装 openai: pip install openai

运行方式：
  python basic_chat.py
"""

from openai import OpenAI

# ============================================================
# 0. 配置 —— 替换为你的真实 API Key
# ============================================================
API_KEY = "sk-你的APIKey"  # TODO: 替换为真实的 API Key

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=API_KEY,
)

# ============================================================
# 1. 单轮对话
# ============================================================
print("=" * 60)
print("【单轮对话】")
print("=" * 60)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "请用一句话解释什么是大语言模型（LLM）。"},
    ],
    temperature=0.9,
    top_p=1.0,
    extra_body={
        "reasoning_effort": "no_think"
    },
)

# 解析完整响应
message = response.choices[0].message
print(f"模型回答: {message.content}")
print(f"\n--- 完整响应字段 ---")
print(f"响应 ID:      {response.id}")
print(f"模型:         {response.model}")
print(f"创建时间戳:   {response.created}")
print(f"结束原因:     {response.choices[0].finish_reason}")
print(f"提示 token:   {response.usage.prompt_tokens}")
print(f"生成 token:   {response.usage.completion_tokens}")
print(f"总 token:     {response.usage.total_tokens}")

# ============================================================
# 2. 多轮对话
# ============================================================
print("\n" + "=" * 60)
print("【多轮对话】")
print("=" * 60)

# 维护 messages 列表以实现上下文延续
messages = [
    {"role": "system", "content": "你是一个乐于助人的助手，回答简洁明了。"},
    {"role": "user", "content": "法国的首都是什么？"},
]

print(f"User: {messages[-1]['content']}")
response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.7,
    top_p=1.0,
    extra_body={"reasoning_effort": "no_think"},
)
assistant_msg = response.choices[0].message
messages.append({"role": "assistant", "content": assistant_msg.content})
print(f"Assistant: {assistant_msg.content}")

# 第二轮：追问
messages.append({"role": "user", "content": "那里有什么著名的地标建筑？"})
print(f"\nUser: {messages[-1]['content']}")

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.7,
    top_p=1.0,
    extra_body={"reasoning_effort": "no_think"},
)
assistant_msg = response.choices[0].message
messages.append({"role": "assistant", "content": assistant_msg.content})
print(f"Assistant: {assistant_msg.content}")

# 第三轮：进一步追问
messages.append({"role": "user", "content": "你能用英文介绍一下那个地标吗？"})
print(f"\nUser: {messages[-1]['content']}")

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.7,
    top_p=1.0,
    extra_body={"reasoning_effort": "no_think"},
)
assistant_msg = response.choices[0].message
messages.append({"role": "assistant", "content": assistant_msg.content})
print(f"Assistant: {assistant_msg.content}")

print(f"\n--- 多轮对话统计 ---")
print(f"总消息数: {len(messages)}")
print(f"总 token 数: {response.usage.total_tokens}")
