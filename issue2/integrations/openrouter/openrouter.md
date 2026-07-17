# 在 OpenRouter 中使用 Hy3

> 🌐 English version: [openrouter.en.md](openrouter.en.md)

## 工具简介

[OpenRouter](https://openrouter.ai) 是一个统一的 LLM API 网关，聚合了 200+ 模型。它的核心优势是**无需自建 GPU 服务**，统一按量计费，一个 API Key 即可调用包括 Hy3 在内的所有模型。

## 适用场景

- 零部署快速体验 Hy3
- 在多个模型之间切换对比（A/B Testing）
- 不想维护 GPU 集群的个人开发者

## 版本要求

| 项 | 要求 |
|:---|:---|
| OpenRouter 账号 | 免费注册即可 |
| API Key | 在 [Keys 页面](https://openrouter.ai/keys) 创建 |
| 余额 | 按模型消耗付费（Hy3 约 $0.50/M tokens 级别） |
| 客户端 | 任意支持 OpenAI API 的客户端均可 |

## 配置项

### 通用客户端配置（Python / Node.js / 任意 OpenAI SDK）

```
base_url    = "https://openrouter.ai/api/v1"
api_key     = "sk-or-v1-你的OpenRouter密钥"
model       = "tencent/hy3"              # 注意：不是 "hy3"
```

### 关键参数映射

| Hy3 原生参数 | OpenRouter 使用方式 |
|:---|:---|
| `reasoning_effort` | 通过 `extra_body` 或 `provider.preferences` 透传 |
| `temperature` | 直接透传，推荐 `0.9` |
| `top_p` | 直接透传，推荐 `1.0` |
| `max_tokens` | 限制回复长度 |

## 端到端 Demo

### Python 示例：调用 Hy3 进行深度推理

```python
import requests
import json

API_KEY = "sk-or-v1-你的密钥"
BASE_URL = "https://openrouter.ai/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": "tencent/hy3",
    "messages": [
        {
            "role": "user",
            "content": "请用 Rust 实现一个线程安全的 LRU 缓存，包含详细的注释和单元测试。"
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 4096,
    # 开启深度推理模式
    "extra_body": {
        "chat_template_kwargs": {"reasoning_effort": "high"}
    }
}

response = requests.post(
    f"{BASE_URL}/chat/completions",
    headers=headers,
    json=payload,
    timeout=120
)

print(response.json()["choices"][0]["message"]["content"])
```

### 终端 cURL 一行测试

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer sk-or-v1-你的密钥" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tencent/hy3",
    "messages": [{"role": "user", "content": "用一句话介绍你自己"}],
    "temperature": 0.9,
    "top_p": 1.0,
    "extra_body": {"chat_template_kwargs": {"reasoning_effort": "no_think"}}
  }'
```

### 预期输出

```
我是腾讯混元 Hy3，一个 295B 参数的混合专家（MoE）大语言模型，
擅长推理、编程、长文本处理和 Agent 任务。
```

## 常见注意事项

| 问题 | 原因 | 解决方案 |
|:---|:---|:---|
| `model not found` | 模型 ID 写错 | 确认使用 `tencent/hy3` 而非 `hy3` |
| `provider error` | Hy3 在 OpenRouter 上不可用 | 登录 OpenRouter 检查 Hy3 状态 |
| `401 Unauthorized` | API Key 拼写错误或未加前缀 | 确认使用完整 `sk-or-v1-xxx` 格式 |
| 推理耗时较长 | `reasoning_effort=high` 会生成思维链 | 对简单任务使用 `no_think` |
| `max_tokens` 截断 | 回复被截断 | 调大 `max_tokens` 或不设置（建议 4096+） |
| 费用较高 | Hy3 在 OpenRouter 上按 token 计费 | 监控用量，使用 `no_think` 降低消耗 |


[← 返回索引](../README.md)
