# Hy3 API Quickstart

通过本指南，您可以在 5 分钟内完成第一次 Hy3 API 调用，并了解核心功能。

## 1. 获取 API Key

访问 [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey)：
- 点击 **创建 API Key**
- 名称任意，如 `Hy3-dev`
- **可访问范围** 选择 **限定范围**，并勾选 `Hy3 preview`
- 创建后 **立即复制并保存** API Key（只显示一次）

## 2. 设置环境变量

import os
from openai import OpenAI

client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=os.environ.get("TOKENHUB_API_KEY"),
)

response = client.chat.completions.create(
    model="hy3-preview",
    messages=[{"role": "user", "content": "请用一句话介绍你自己"}],
)

print(response.choices[0].message.content)