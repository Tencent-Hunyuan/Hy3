# Hy3 on OpenRouter

[OpenRouter](https://openrouter.ai/) 是统一的 LLM API 网关，可直接调用 Hy3，无需自行部署。

## 1. 安装与版本要求

- 无需安装客户端，纯 API 服务
- 任意支持 OpenAI SDK 的环境（`openai` Python 包 ≥ 1.0，或 Node `openai` ≥ 4.0）
- 已验证 Hy3 在 OpenRouter 上架：模型 slug `tencent/hy3`，上下文 262K，定价 `$0.20 / $0.80` per 1M tokens（in/out）

## 2. 配置项

| 配置项 | 值 |
|--------|-----|
| 协议 | OpenAI 兼容 (`/v1/chat/completions`) |
| Base URL | `https://openrouter.ai/api/v1` |
| Model 名 | `tencent/hy3` |
| 鉴权 | `Authorization: Bearer <OPENROUTER_API_KEY>` |
| API Key 获取 | https://openrouter.ai/settings/keys |

## 3. 端到端流程

### 步骤 1：配置（拿到 Key）

注册 OpenRouter → Settings → Keys → 生成 API Key，导出到环境变量：

```bash
export OPENROUTER_API_KEY=sk-or-v1-xxxx
```

### 步骤 2：第一次对话

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "tencent/hy3",
    "messages": [{"role": "user", "content": "你好，介绍一下你自己"}]
  }'
```

### 步骤 3：跑通一个真实任务（Python 脚本）

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-v1-xxxx",
)

# 真实任务：把一段中文产品描述翻译成英文并生成 3 个卖点
resp = client.chat.completions.create(
    model="tencent/hy3",
    messages=[{
        "role": "user",
        "content": "把下面的产品描述翻译成英文，并提炼 3 个卖点：\n"
                   "一款保温杯，24 小时保温，316 不锈钢内胆，容量 500ml。"
    }],
    temperature=0.7,
)
print(resp.choices[0].message.content)
```

## 4. 端到端 demo（截图 / GIF）

> 截图位置：见 [screenshots 指南 #1](../../screenshots/README.md#1-openrouter)
> - 图 1：OpenRouter 模型页 `tencent/hy3` 的定价与上下文信息
> - 图 2：第一次对话返回结果
> - 图 3：真实任务（翻译+卖点提炼）输出

## 5. 常见注意事项

- OpenRouter 按 token 计费，可在 [Pricing](https://openrouter.ai/models/tencent/hy3/pricing) 查看
- 支持 `stream: true`，与标准 OpenAI API 一致
- 可通过 `extra_body` 传 `reasoning_effort` 控制思考模式（`no_think` / `low` / `high`）
- 免费额度有限，调用前需绑定支付方式
- 默认会带上 OpenRouter 的 HTTP Referer / Title 头，本地自建服务无需关心
