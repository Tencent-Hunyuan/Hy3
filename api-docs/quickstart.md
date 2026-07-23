# Hy3 API Quickstart

## 目录

- [Hy3 API Quickstart](#hy3-api-quickstart)
  - [目录](#目录)
  - [前置条件](#前置条件)
  - [基础信息](#基础信息)
  - [最小可运行示例](#最小可运行示例)
    - [curl](#curl)
    - [Python (openai SDK)](#python-openai-sdk)
  - [参数说明](#参数说明)
    - [基础参数](#基础参数)
    - [消息格式](#消息格式)
    - [推荐参数](#推荐参数)
  - [思考模式（Reasoning Mode）](#思考模式reasoning-mode)
  - [Tool Calling](#tool-calling)
  - [速率限制](#速率限制)
  - [常见报错排查](#常见报错排查)
    - [401 Unauthorized](#401-unauthorized)
    - [429 Too Many Requests](#429-too-many-requests)
    - [400 Bad Request — invalid model](#400-bad-request--invalid-model)
    - [400 Bad Request — max\_tokens too large](#400-bad-request--max_tokens-too-large)
    - [500 Internal Server Error](#500-internal-server-error)
    - [ConnectionError / Timeout](#connectionerror--timeout)
    - [Stream 中途断开](#stream-中途断开)

---

## 前置条件

- **API Key**：从腾讯混元平台获取（[aistudio.tencent.com](https://aistudio.tencent.com/)）
- **Python ≥ 3.8**（如使用 Python SDK）
- **openai SDK**：`pip install openai`

---

## 基础信息

| 项目 | 值 |
|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| Model ID | `hy3` |
| API 协议 | OpenAI-compatible `/v1/chat/completions` |
| 认证方式 | Bearer Token（API Key 传入 `Authorization` 头） |
| 请求方式 | POST |
| Content-Type | `application/json` |
| 支持流式 | ✅（`stream: true`） |
| 支持 Tool Calling | ✅ |
| 支持思考模式 | ✅（`reasoning_effort`） |
| 上下文长度 | 256K tokens |

---

## 最小可运行示例

### curl

```bash
curl https://tokenhub.tencentmaas.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512
  }'
```

**预期响应：**

```json
{
  "id": "chatcmpl-xxxxxxxxxxxxxxxxx",
  "object": "chat.completion",
  "created": 1718432000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是腾讯混元团队研发的 Hy3 大语言模型..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 48,
    "total_tokens": 63
  }
}
```

### Python (openai SDK)

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",  # 替换为你的 API Key
    base_url="https://tokenhub.tencentmaas.com/v1",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好，请介绍一下你自己"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
)

print(response.choices[0].message.content)
```

**预期输出：**

```
我是混元，是由腾讯开发的大模型。
我专注于基础信息处理与逻辑响应，能解答各类问题、辅助创作和提供信息支持。
如果有具体需求，随时告诉我，我会尽力帮你～
```

---

## 参数说明

### 基础参数

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `model` | `string` | — | 模型名，固定为 `"hy3"` |
| `messages` | `array` | — | 对话消息列表，见下方消息格式 |
| `temperature` | `float` | `0.9` | 采样温度，范围 `[0.0, 2.0]`。值越低输出越确定，越高越随机 |
| `top_p` | `float` | `1.0` | 核采样（nucleus sampling），范围 `[0.0, 1.0]`。只从累积概率 ≥ top_p 的 token 中采样 |
| `max_tokens` | `int` | — | 最大生成 token 数。不设则模型自行决定。注意：该值包含思考过程中的 token |
| `stop` | `string` / `array` | — | 停止词。遇到时立即停止生成。可传单个字符串或字符串数组 |
| `stream` | `bool` | `false` | 是否流式返回。设为 `true` 时响应以 SSE 格式逐 token 推送 |
| `seed` | `int` | — | 随机种子。设置后相同输入产生更一致的输出 |
| `tools` | `array` | — | 工具定义列表，见 [Tool Calling](#tool-calling) 章节 |
| `tool_choice` | `string` / `object` | `"auto"` | 工具选择策略：`"auto"`、`"none"`、`"required"` 或指定工具 |

### 消息格式

每条消息包含以下字段：

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `role` | `string` | `"system"`、`"user"`、`"assistant"` 或 `"tool"` |
| `content` | `string` | 消息正文。当 role 为 `"tool"` 时，为工具返回结果 |
| `name` | `string` | （可选）发送者名称 |
| `tool_calls` | `array` | （仅 assistant）工具调用列表 |
| `tool_call_id` | `string` | （仅 tool）对应的工具调用 ID |

### 推荐参数

> 生产环境推荐 `temperature=0.9`，`top_p=1.0`。需要高确定性输出（如代码生成）时可降至 `temperature=0.1`。

---

## 思考模式（Reasoning Mode）

Hy3 支持快慢思考融合：对简单问题直接回复，对复杂问题展开深度思维链推理。

通过 `extra_body` 传入 `chat_template_kwargs.reasoning_effort` 控制：

| 值 | 说明 | 适用场景 |
|:---|:---|:---|
| `"no_think"` | 关闭思考，直接回复（**默认**） | 日常对话、简单问答 |
| `"high"` | 深度思维链推理 | 数学、编程、逻辑推理等复杂任务 |

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# 深度推理模式
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "证明根号2是无理数"},
    ],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)

# 回复中可获取思考过程和最终答案
print(response.choices[0].message.content)
```

> **注意**：开启思考模式后，`max_tokens` 限制同时适用于思考内容和最终回答。复杂推理任务建议设置较大的 `max_tokens`（如 4096 或更高）。

---

## Tool Calling

Hy3 支持 OpenAI 兼容的工具调用。完整示例见 [examples/04-tool-calling.md](examples/04-tool-calling.md)。

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"}
                },
                "required": ["city"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "北京天气怎么样？"}],
    tools=tools,
    tool_choice="auto",
)

# 检查是否有工具调用
if response.choices[0].message.tool_calls:
    for tc in response.choices[0].message.tool_calls:
        print(f"调用工具: {tc.function.name}")
        print(f"参数: {tc.function.arguments}")
```

---

## 速率限制

| 限制类型 | 默认值 | 说明 |
|:---|:---|:---|
| RPM（每分钟请求数） | 视 API Key 等级而定 | 超出返回 `429 Too Many Requests` |
| TPM（每分钟 Token 数） | 视 API Key 等级而定 | 超出返回 `429 Too Many Requests` |
| 最大并发数 | 视 API Key 等级而定 | 超出返回 `429` 或连接拒绝 |

> 具体限额请以腾讯混元平台控制台显示为准。遇到限流时请实现指数退避重试（见 [examples/06-error-handling-retry.md](examples/06-error-handling-retry.md)）。

---

## 常见报错排查

### 401 Unauthorized

```json
{"error": {"message": "Unauthorized", "type": "authentication_error"}}
```

**原因**：API Key 缺失或无效。
**解决**：检查 `Authorization: Bearer <KEY>` 头是否正确设置，确认 API Key 未过期。

---

### 429 Too Many Requests

```json
{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}
```

**原因**：超出 RPM / TPM 限制。
**解决**：
1. 降低请求频率
2. 实现指数退避重试（见 example 06）
3. 升级 API Key 等级

---

### 400 Bad Request — invalid model

```json
{"error": {"message": "The model `xxx` does not exist", "type": "invalid_request_error"}}
```

**原因**：模型名错误。
**解决**：确认 `model` 参数为 `"hy3"`（小写）。

---

### 400 Bad Request — max_tokens too large

```json
{"error": {"message": "max_tokens is too large", "type": "invalid_request_error"}}
```

**原因**：`max_tokens` + prompt tokens 超出上下文窗口（256K）。
**解决**：减小 `max_tokens` 或缩短输入消息。

---

### 500 Internal Server Error

```json
{"error": {"message": "Internal server error", "type": "server_error"}}
```

**原因**：服务端临时故障。
**解决**：等待几秒后重试，建议实现自动重试逻辑。

---

### ConnectionError / Timeout

**原因**：网络不可达或请求超时。
**解决**：
1. 检查网络连通性：`curl -I https://tokenhub.tencentmaas.com/v1/models`
2. 适当增加超时时间：`client = OpenAI(base_url=..., timeout=60.0)`
3. 设置合理的重试策略：`client = OpenAI(base_url=..., max_retries=3)`

---

### Stream 中途断开

**原因**：网络波动或服务端超时。
**解决**：
1. 实现流式重连 + 断点续传
2. 使用更短的 `max_tokens` 减少单次连接时间
3. 客户端设置更长的 `timeout`

---

> 更多完整可运行示例请查看 [examples/](examples/) 目录。
