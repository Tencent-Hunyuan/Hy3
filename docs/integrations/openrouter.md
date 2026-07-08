# Hy3 on OpenRouter

OpenRouter 是一个统一的 LLM API 网关，可直接调用 Hy3 而无需自行部署。

## 配置

1. 注册 [OpenRouter](https://openrouter.ai/)
2. 在 [Settings](https://openrouter.ai/settings/keys) 页面生成 API Key
3. 搜索模型 `tencent/hy3` 并确认可用

### API 参数

| 参数 | 值 |
|------|-----|
| Base URL | `https://openrouter.ai/api/v1` |
| Model | `tencent/hy3` |
| Auth | `Bearer <YOUR_API_KEY>` |

## 快速开始

### cURL

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "tencent/hy3",
    "messages": [
      {"role": "user", "content": "解释量子计算的基本原理"}
    ],
    "temperature": 0.7
  }'
```

### Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="YOUR_API_KEY",
)

response = client.chat.completions.create(
    model="tencent/hy3",
    messages=[{"role": "user", "content": "解释量子计算的基本原理"}],
    temperature=0.7,
)
print(response.choices[0].message.content)
```

## 注意事项

- OpenRouter 按 token 计费，可在 [Pricing](https://openrouter.ai/models/tencent/hy3/pricing) 查看
- 支持 stream 模式，与标准 OpenAI API 一致
- 可通过 extra_body 传递 `reasoning_effort` 参数控制思考模式
- 免费额度有限，需绑定支付方式

## 截图

> 待补充：OpenRouter 模型选择页面截图 + 首次对话截图
