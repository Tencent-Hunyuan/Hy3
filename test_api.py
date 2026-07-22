### Python (OpenAI SDK)
from openai import OpenAI

# 初始化客户端
client = OpenAI(
    api_key="sk-nfCJ6gNuxMHId8GT95myuS88L3MZtouSiVozv5gHu0DUni22",  # 替换为你申请的 Key
    base_url="https://tokenhub.tencentmaas.com/v1"
)

# 发送请求
response = client.chat.completions.create(
    model="hy3-preview",
    messages=[
        {"role": "system", "content": "你是一个专业的 AI 助手"},
        {"role": "user", "content": "用一句话介绍腾讯混元大模型"}
    ],
    temperature=0.7
)

print(response.choices[0].message.content)