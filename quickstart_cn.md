<p align="left">
   <a href="quickstart.md">English</a> ｜ 中文
</p>

# Hy3 API 快速开始

本文档面向第一次调用 Hy3 API 的开发者。使用腾讯云 TokenHub 托管 API 时，不需要在本地部署 Hy3 模型。

如果只想完成第一次调用，请按下面的步骤操作：

1. 创建腾讯云 TokenHub API Key。
2. 将 API Key 保存到环境变量。
3. 使用 Chat Completions API 发起一次请求。

## 1. 创建 API Key

前往腾讯云 [TokenHub API Key 管理](https://console.cloud.tencent.com/tokenhub/apikey) 页面创建 API Key。

请不要将 API Key 直接写入代码、文档或提交到 Git。建议在当前终端中设置环境变量：

```bash
export HY3_API_KEY="你的 TokenHub API Key"
```

如果 API Key 曾经被写入公开仓库、截图或聊天记录，请先在控制台禁用或删除，再重新生成新的 Key。

## 2. 选择 API 协议

Hy3 托管 API 支持两种常见的 OpenAI 兼容协议：

- Chat Completions API：本文档默认使用，适合快速开始、普通对话和流式输出。
- [Responses API](docs/api/responses_cn.md)：适合统一响应格式、状态衔接和更复杂的 Agent 场景。

本文先介绍 Chat Completions API。更详细的 Hy3 模型限制和专用调用方式，请参考 [Hy3 调用指南](https://cloud.tencent.com/document/product/1823/132252)；公共参数、响应字段、工具调用和流式输出说明，请参考 [TokenHub 语言模型调用概览](https://cloud.tencent.com/document/product/1823/130079)。Responses API 的协议差异见[独立说明](docs/api/responses_cn.md)。

## 3. 基础信息

### Base URL

TokenHub 根据服务地域提供不同的接口地址。API Key、服务地域和 Base URL 必须保持一致，不支持跨地域或跨站点调用。

| 地域  | Base URL                                   | 适用范围 |
|-----|--------------------------------------------|------|
| 广州  | `https://tokenhub.tencentmaas.com/v1`      | 中国大陆 |
| 新加坡 | `https://tokenhub-intl.tencentmaas.com/v1` | 全球   |

官方文档还提供对应的备用域名：广州为 `https://tokenhub.tencentmaas.cn/v1` ，新加坡为 `https://tokenhub-intl.tencentmaas.cn/v1` 。建议仅在默认地址不可用时切换备用地址。

### API Key

API Key 通过 HTTP Header 传递：

```http
Authorization: Bearer ${HY3_API_KEY}
```

不要将真实 Key 写入文档、代码、截图或 Git 提交。可以通过 `GET /v1/models` 检查当前 Key 能访问的模型列表：

```bash
curl "https://tokenhub.tencentmaas.com/v1/models" \
  -H "Authorization: Bearer ${HY3_API_KEY}"
```

### Model 名称

Hy3 的模型调用名为：

```text
hy3
```

请求中的 `model` 字段应使用服务 ID，而不是本地 checkpoint 路径。Hy3 同时支持 TokenHub 的 OpenAI Chat Completions、OpenAI Responses 和 Anthropic 协议；本文默认使用 Chat Completions。

### 模型限制与吞吐限制

[模型广场](https://console.cloud.tencent.com/tokenhub/models/detail?modelId=hy3&regionId=1&from=all&Is=sdk-topnav) 于 2026 年 7 月 22 日记录的 Hy3 服务信息如下：

| 项目          |         值 | 说明                             |
|-------------|----------:|--------------------------------|
| 最大输入 Tokens |      192k | 单次请求允许的最大输入长度。                 |
| 最大输出 Tokens |      128k | 单次请求允许的最大输出长度；思考 Token 计入输出额度。 |
| 上下文窗口       |      256k | 输入和输出共同使用的上下文上限。               |
| 最大 TPM      | 1,000,000 | 服务每分钟可处理的输入和输出 Token 总量上限。     |
| 最大 RPM      |        60 | 服务每分钟可处理的请求数上限。                |

前三项是模型容量限制；TPM 和 RPM 属于服务限流信息，可能随地域、套餐、API Key 或账户等级变化。实际调用时，应以模型广场中显示的最新信息为准。

## 4. 第一次调用

本文档默认使用 Chat Completions API。请求由 URL、请求头和 JSON 请求体组成：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "system", "content": "你是一个有帮助的助手。"},
      {"role": "user", "content": "你好"}
    ],
    "stream": false
  }'
```

### 请求说明

#### 请求地址

```text
POST https://tokenhub.tencentmaas.com/v1/chat/completions
```

`POST` 表示向该地址提交一次模型生成请求。

#### 请求头

| 字段              | 类型     | 作用                                  |
|-----------------|--------|-------------------------------------|
| `Authorization` | string | 身份认证，格式为 `Bearer ${HY3_API_KEY}`。   |
| `Content-Type`  | string | 声明请求体为 JSON，固定为 `application/json`。 |

#### 请求体

| 字段                   | 类型              | 必填 | 作用                                   |
|----------------------|-----------------|----|--------------------------------------|
| `model`              | string          | 是  | 模型名称，Hy3 托管 API 使用 `hy3`。            |
| `messages`           | array of object | 是  | 按时间顺序排列的对话消息数组。                      |
| `messages[].role`    | string          | 是  | 消息角色，例如 `system`、`user`、`assistant`。 |
| `messages[].content` | string          | 是  | 当前消息的文本内容。                           |
| `stream`             | boolean         | 否  | 是否启用流式输出。`false` 等待完整结果，`true` 逐段返回。 |

请求中的 `messages` 是数组，因此可以传入多轮对话：

```json
[
  {"role": "system", "content": "你是一个有帮助的助手。"},
  {"role": "user", "content": "我叫小明。"},
  {"role": "assistant", "content": "你好，小明。"},
  {"role": "user", "content": "我叫什么？"}
]
```

### 响应示例

如果请求成功，服务会返回一个 JSON 对象。格式化后如下：

```json
{
  "id": "c27d9b74-497e-4968-8138-530063de4f40",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1784381073,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是你的助手，有什么可以帮你的吗？ 😊"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 22,
    "completion_tokens": 15,
    "total_tokens": 37,
    "prompt_tokens_details": {"cached_tokens": 0},
    "completion_tokens_details": {"reasoning_tokens": 0}
  }
}
```

### 响应字段说明

| 字段                                                 | 类型              | 作用                                        |
|----------------------------------------------------|-----------------|-------------------------------------------|
| `id`                                               | string          | 本次请求的唯一标识，可用于日志追踪和问题排查。                   |
| `object`                                           | string          | 响应对象类型，非流式响应通常为 `chat.completion`。        |
| `model`                                            | string          | 实际处理请求的模型名称。                              |
| `created`                                          | integer         | 请求创建时间，通常为 Unix 时间戳，单位为秒。                 |
| `choices`                                          | array of object | 模型生成结果列表。即使通常只有一个结果，也需要按数组读取。             |
| `choices[].index`                                  | integer         | 当前结果在 `choices` 数组中的索引，通常从 `0` 开始。        |
| `choices[].message`                                | object          | 模型返回的消息对象。                                |
| `choices[].message.role`                           | string          | 返回消息的角色，通常为 `assistant`。                  |
| `choices[].message.content`                        | string or null  | 模型生成的文本内容。读取模型回复时通常使用这个字段。                |
| `choices[].finish_reason`                          | string or null  | 生成结束原因，例如 `stop` 表示正常结束。工具调用或长度限制可能对应其他值。 |
| `usage`                                            | object          | 本次请求的 Token 使用统计。                         |
| `usage.prompt_tokens`                              | integer         | 输入消息消耗的 Token 数量。                         |
| `usage.completion_tokens`                          | integer         | 模型输出消耗的 Token 数量。                         |
| `usage.total_tokens`                               | integer         | 总 Token 数，通常等于输入和输出 Token 数之和。            |
| `usage.prompt_tokens_details.cached_tokens`        | integer         | 命中缓存的输入 Token 数量。没有缓存时通常为 `0`。            |
| `usage.completion_tokens_details.reasoning_tokens` | integer         | 思考过程消耗的 Token 数量；未启用或服务未返回时可能为 `0`。       |

最常用的取值方式是：

```text
choices[0].message.content
```

其中，`choices[0]` 表示取第一个生成结果，`message.content` 表示取该结果中的文本内容。

> 注意：启用 `stream: true` 后，响应会拆成多个流式 chunk，响应结构与上面的完整 JSON 不完全相同，应参考下一节解析。

### Python OpenAI SDK

先安装 OpenAI Python SDK：

```bash
pip install -U openai
```

SDK 会通过 OpenAI 兼容接口访问 Hy3。示例默认使用广州 Base URL；如果 API Key 属于新加坡地域，请将 `HY3_BASE_URL` 改为 `https://tokenhub-intl.tencentmaas.com/v1` 。API Key 和 Base URL 必须属于同一地域。

```python
import os

from openai import OpenAI

api_key = os.environ["HY3_API_KEY"]
base_url = os.getenv(
    "HY3_BASE_URL",
    "https://tokenhub.tencentmaas.com/v1",
)

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "你好，请简单介绍一下你自己。"},
    ],
    stream=False,
)

print(response.choices[0].message.content)
```

运行前，请先在当前终端设置 API Key：

```bash
export HY3_API_KEY="你的 TokenHub API Key"
```

如果使用新加坡地域，还需要设置：

```bash
export HY3_BASE_URL="https://tokenhub-intl.tencentmaas.com/v1"
```

代码通过 `response.choices[0].message.content` 读取模型回复。示例文件为 `examples/01_basic_chat.py`，可以使用 uv 运行：

```bash
uv run --env-file .env python examples/01_basic_chat.py
```

如果不使用 `.env` 文件，也可以直接在当前终端导出 `HY3_API_KEY` 和可选的 `HY3_BASE_URL`，再运行：

```bash
uv run python examples/01_basic_chat.py
```

后续的流式输出、工具调用和错误重试示例也统一放在 `examples/` 目录中。

## 5. 多轮对话

通过 `messages` 数组传递系统提示和历史对话，模型会按照消息顺序理解上下文并生成下一轮回复。消息通常按以下顺序排列：

```text
system（可选）→ user → assistant → user → ...
```

应以 `user` 消息结束本轮请求：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "system", "content": "你是一个有帮助的助手。"},
      {"role": "user", "content": "你好"},
      {"role": "assistant", "content": "你好，有什么可以帮你的吗？"},
      {"role": "user", "content": "我想知道 37 × 24 的计算结果。"}
    ],
    "stream": false
  }'
```

当历史对话包含思考类响应时，回写 `assistant` 消息时建议同时保留 `content` 和服务返回的思考相关字段，以避免上下文丢失。应用是否需要回写这些字段，应以 TokenHub 的 Hy3 专用协议说明为准。

## 6. 流式输出

将 `stream` 设置为 `true` 后，服务会通过 Server-Sent Events（SSE）逐段返回结果：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

示例响应：

```text
data: {"id":"6f649f1b-09fa-46db-bbf2-b91ef3ac12c8","object":"chat.completion.chunk","created":1784688338,"model":"hy3","choices":[{"index":0,"delta":{"role":"assistant"}}]}

data: {"id":"6f649f1b-09fa-46db-bbf2-b91ef3ac12c8","object":"chat.completion.chunk","created":1784688338,"model":"hy3","choices":[{"index":0,"delta":{"content":"你好！"}}]}

data: {"id":"6f649f1b-09fa-46db-bbf2-b91ef3ac12c8","object":"chat.completion.chunk","created":1784688338,"model":"hy3","choices":[{"index":0,"delta":{"content":"有什么可以帮你的吗？"},"finish_reason":"stop"}]}

data: [DONE]
```

流式响应的每一行以 `data:` 开头，后面是一个 JSON chunk：

- 第一段通常包含 `delta.role`，用于声明返回角色。
- 中间的 chunk 通过 `delta.content` 返回部分文本，客户端需要按顺序拼接。
- 最后一段通常包含 `finish_reason: "stop"`，表示本次生成正常结束。
- `data: [DONE]` 表示整个流结束，不是 JSON 对象。

因此，流式响应不能按照非流式响应的 `choices[0].message.content` 一次性读取。

### 在流式响应中返回 usage

如果希望在最后一个 chunk 中获取完整的 `usage` 统计，需要将 `stream_options.include_usage` 设置为 `true`：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true,
    "stream_options": {"include_usage": true}
  }'
```

启用后，最后一个包含 `choices: []` 的 chunk 会返回 `usage`；`data: [DONE]` 仍然表示整个流结束。

## 7. 深度思考

### 开启或关闭思考模式

通过 `thinking` 参数控制是否开启思考模式：

```json
"thinking": {"type": "enabled"}
```

关闭思考模式：

```json
"thinking": {"type": "disabled"}
```

Hy3 默认关闭思考模式，即 `thinking.type` 默认为 `disabled`。

下面使用一个简短、可复核的数学问题演示开启思考模式：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "请计算 37 × 24，并用一句话说明结果。"}],
    "thinking": {"type": "enabled"},
    "stream": false
  }'
```

示例中重点关注 `choices[0].message.content`。服务可能额外返回 `reasoning_content` 等思考相关字段；应用不应依赖或展示模型的原始思考过程，除非服务协议和产品需求明确要求这样做。

### 配置推理深度

通过 `reasoning_effort` 参数控制推理强度。推理强度越高，通常回答会更充分，但延迟和 Token 消耗也可能增加。

| `reasoning_effort` | 说明                                 |
|--------------------|------------------------------------|
| `low`              | 轻量推理，速度较快，适合简单任务。                  |
| `medium`           | 在速度和推理能力之间取得平衡，适合大多数任务。            |
| `high`             | 深度推理，适合高难度数学、编程或复杂逻辑任务，但延迟和成本通常更高。 |

Hy3 的默认 `reasoning_effort` 为 `low`。

> 注意：Hy3 正式版在 Tool Calling 场景下具备 adaptive thinking 能力，可以根据任务复杂度自动调整推理深度。为兼容部分工具调用场景，当请求携带 `tools` 且 `reasoning_effort` 设置为 `low` 时，API 可能会将其自动映射为 `high`。

## 8. 工具调用

工具调用通常包含两次模型请求和一次本地函数执行：

1. 第一次请求中通过 `tools` 声明模型可以调用的函数。
2. 如果模型返回 `tool_calls`，业务代码解析参数并执行对应的本地函数。
3. 第二次请求将工具结果以 `role: "tool"` 消息回填，让模型生成最终的自然语言回答。

模型只负责提出工具调用建议，不会直接执行你的本地函数；函数的实际执行、权限控制和异常处理都由业务代码负责。

### 第一次请求：声明工具

下面的示例声明一个查询天气的函数，并允许模型自动决定是否调用它。注意：`parameters` 必须是合法的 JSON Schema，不能包含尾随逗号。

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "深圳今天天气怎么样？"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "获取指定城市的当前天气信息",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {
                "type": "string",
                "description": "城市名称，例如：深圳"
              }
            },
            "required": ["city"]
          }
        }
      }
    ],
    "tool_choice": "auto",
    "stream": false
  }'
```

其中：

- `tools` 是工具定义数组。
- `type: "function"` 表示工具类型为函数。
- `function.name` 是业务代码中实际要执行的函数名。
- `function.description` 用于帮助模型判断何时使用该工具。
- `function.parameters` 使用 JSON Schema 描述函数参数。
- `tool_choice: "auto"` 表示由模型自动决定是否调用工具。

### 工具定义字段说明

| 字段                            | 类型               | 作用                                               |
|-------------------------------|------------------|--------------------------------------------------|
| `tools`                       | array            | 可用工具列表。一次请求可以声明多个工具。                             |
| `tools[].type`                | string           | 工具类型。当前函数调用使用 `function`。                        |
| `tools[].function`            | object           | 函数工具的具体定义。                                       |
| `function.name`               | string           | 函数名称。业务代码根据这个名称选择并执行对应函数。建议使用字母、数字和下划线，并保持名称稳定。  |
| `function.description`        | string           | 函数用途说明。模型会参考它判断什么时候应该调用该函数，因此应写清楚功能和适用场景。        |
| `function.parameters`         | object           | 使用 JSON Schema 描述函数参数的结构、类型和约束。                  |
| `parameters.type`             | string           | 参数根节点的类型。函数参数通常是一个 JSON 对象，因此使用 `object`。        |
| `parameters.properties`       | object           | 定义参数对象中的字段。对象的每个 key 是参数名，对应的 value 描述该参数的类型和含义。 |
| `properties.city`             | object           | 名为 `city` 的参数定义。这里的名称必须和业务函数实际读取的字段一致。           |
| `properties.city.type`        | string           | `city` 参数的 JSON 类型。本例中为 `string`。                |
| `properties.city.description` | string           | 参数说明，用于帮助模型生成正确的参数值。                             |
| `parameters.required`         | array of string  | 必填参数名称列表。本例中 `city` 必须出现在工具调用参数中。                |
| `tool_choice`                 | string or object | 控制工具调用策略。常用值包括 `auto`、`none` 和 `required`。       |

`properties` 可以同时定义多个参数。例如，如果天气函数还需要查询温度单位，可以这样扩展：

```json
{
  "type": "object",
  "properties": {
    "city": {
      "type": "string",
      "description": "城市名称，例如：深圳"
    },
    "unit": {
      "type": "string",
      "enum": ["celsius", "fahrenheit"],
      "description": "温度单位"
    }
  },
  "required": ["city"]
}
```

在这个例子中，`city` 是必填参数，`unit` 是可选参数；`enum` 限制了 `unit` 只能取 `celsius` 或 `fahrenheit`。

`tool_choice` 的常见取值如下：

| 值                                                       | 作用                  |
|---------------------------------------------------------|---------------------|
| `"auto"`                                                | 由模型自动决定是否调用工具。      |
| `"none"`                                                | 禁止调用工具，只允许直接生成文本回复。 |
| `"required"`                                            | 要求模型调用至少一个工具。       |
| `{"type":"function","function":{"name":"get_weather"}}` | 强制调用指定名称的函数。        |

### 模型返回工具调用

如果模型决定调用工具，响应中的 `finish_reason` 通常为 `tool_calls`，并在 `message.tool_calls` 中返回函数名和参数。下面是一次真实的 Hy3 响应：

```json
{
  "id": "4aec87ee-6f19-4a23-9d9c-97f3480432a3",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1784707500,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "",
        "tool_calls": [
          {
            "id": "chatcmpl-tool-052c157ea6404545840ed45cc35ee1c9",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"city\": \"深圳\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 208,
    "completion_tokens": 20,
    "total_tokens": 228,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 0
    }
  }
}
```

业务代码需要解析 `function.name` 和 `function.arguments`，执行对应函数。这里的 `arguments` 是 JSON 字符串，解析后得到：

```json
{
  "city": "深圳"
}
```

接下来，业务代码应根据 `function.name` 调用本地实现的 `get_weather` 函数。例如，函数返回以下结果：

```json
{
  "city": "深圳",
  "weather": "晴",
  "temperature": 28
}
```

### 工具调用响应字段说明

| 字段                                | 类型             | 作用                                         |
|-----------------------------------|----------------|--------------------------------------------|
| `message.tool_calls`              | array          | 模型请求业务代码执行的工具调用列表。一次响应可能包含多个调用。            |
| `tool_calls[].id`                 | string         | 当前工具调用的唯一标识。回填工具结果时，必须原样放入 `tool_call_id`。 |
| `tool_calls[].type`               | string         | 工具调用类型，本例为 `function`。                     |
| `tool_calls[].function.name`      | string         | 需要执行的函数名称。                                 |
| `tool_calls[].function.arguments` | string         | 函数参数的 JSON 字符串，需要反序列化后再传给本地函数。             |
| `message.content`                 | string or null | 工具调用阶段通常为空字符串或 `null`，最终回答阶段才包含自然语言文本。     |
| `finish_reason`                   | string         | `tool_calls` 表示模型请求调用工具；`stop` 表示模型完成最终回答。 |
| `role: "tool"`                    | string         | 表示这条消息是工具执行结果，而不是用户或模型消息。                  |
| `tool_call_id`                    | string         | 将工具结果关联到对应的 `tool_calls[].id`。             |
| `tool.content`                    | string         | 工具执行结果。通常将结构化结果序列化为 JSON 字符串后传回。           |

### 第二次请求：回填工具结果

工具执行完成后，需要将两类消息回填到下一次请求的 `messages` 中：

1. 模型刚刚返回的 `assistant` 消息，其中必须保留完整的 `tool_calls`。
2. 工具执行结果，使用 `role: "tool"`，并通过 `tool_call_id` 关联原始工具调用。

假设 `get_weather` 返回深圳天气晴朗、温度 28℃，下一次请求如下：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "深圳今天天气怎么样？"},
      {
        "role": "assistant",
        "content": "",
        "tool_calls": [
          {
            "id": "chatcmpl-tool-052c157ea6404545840ed45cc35ee1c9",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"city\": \"深圳\"}"
            }
          }
        ]
      },
      {
        "role": "tool",
        "tool_call_id": "chatcmpl-tool-052c157ea6404545840ed45cc35ee1c9",
        "content": "{\"city\":\"深圳\",\"weather\":\"晴\",\"temperature\":28}"
      }
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "获取指定城市的当前天气信息",
          "parameters": {
            "type": "object",
            "properties": {
              "city": {
                "type": "string",
                "description": "城市名称，例如：深圳"
              }
            },
            "required": ["city"]
          }
        }
      }
    ],
    "tool_choice": "auto",
    "stream": false
  }'
```

模型收到工具结果后，通常会返回普通的 assistant 消息，例如：

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "深圳当前天气晴朗，温度为 28℃。"
      },
      "finish_reason": "stop"
    }
  ]
}
```

`tool_call_id` 必须与模型返回的 `tool_calls[].id` 完全一致，否则模型无法将工具结果对应到原始调用。模型收到工具结果后，才会生成最终的自然语言回复。

> 当启用思考模式且模型响应中包含 `reasoning_content` 时，后续请求应按 TokenHub 的 Hy3 协议要求保留对应的历史字段。不要自行伪造 `reasoning_content`；如果服务没有返回该字段，就不要在下一轮请求中添加。

### 交错式思考模式（Interleaved Thinking）

[交错式思考模式](https://cloud.tencent.com/document/product/1823/130930)将思考能力与工具调用结合起来：模型可以在生成最终答案前，交替进行多轮思考和工具调用，从而提升复杂 Agent 任务中的执行稳定性和回答质量。

它不需要新地请求格式，仍然使用前文介绍的 `thinking`、`reasoning_effort` 和 `tools` 参数。与普通工具调用相比，模型可能在一次任务中多次调用工具；业务代码需要循环处理每次返回的 `tool_calls`，直到模型返回最终回答。

## 9. 结构化输出

通过 `response_format` 可以约束模型按照指定的 JSON Schema 生成结果，适合信息抽取、结构化数据生成等场景。

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {
        "role": "user",
        "content": "请从以下文本中提取人物信息：张三，35 岁，是一名高级软件工程师，擅长 Python、Java 和机器学习。"
      }
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "person_info",
        "schema": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "人物姓名"
            },
            "age": {
              "type": "integer",
              "description": "年龄"
            },
            "occupation": {
              "type": "string",
              "description": "职业"
            },
            "skills": {
              "type": "array",
              "items": {"type": "string"},
              "description": "技能列表"
            }
          },
          "required": ["name", "age", "occupation", "skills"]
        }
      }
    },
    "stream": false
  }'
```

### 请求字段说明

| 字段                            | 类型              | 作用                          |
|-------------------------------|-----------------|-----------------------------|
| `response_format`             | object          | 指定模型输出格式。                   |
| `response_format.type`        | string          | 输出格式类型。本例使用 `json_schema`。  |
| `response_format.json_schema` | object          | JSON Schema 配置。             |
| `json_schema.name`            | string          | Schema 名称，用于标识这套输出结构。       |
| `json_schema.schema`          | object          | 实际的 JSON Schema。            |
| `schema.type`                 | string          | 根节点类型。本例为 `object`。         |
| `schema.properties`           | object          | 定义输出对象中的字段及其类型。             |
| `schema.required`             | array of string | 必须返回的字段名称列表。                |
| `properties.skills.type`      | string          | `skills` 是数组，因此类型为 `array`。 |
| `properties.skills.items`     | object          | 定义数组元素的类型。本例要求每个技能都是字符串。    |

### 响应示例

结构化输出通常仍然位于 `choices[0].message.content` 中，但 `content` 的值是一个 JSON 字符串：

```json
{
  "id": "f9a779b0-ba60-433e-9245-5df2e5a47500",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1784710662,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "{\n  \"age\": 35,\n  \"name\": \"张三\",\n  \"occupation\": \"高级软件工程师\",\n  \"skills\": [\n    \"Python\",\n    \"Java\",\n    \"机器学习\"\n  ]\n}"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 40,
    "completion_tokens": 47,
    "total_tokens": 87,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 0
    }
  }
}
```

外层响应字段与普通 Chat Completions 响应相同：

| 字段                           | 类型      | 作用                            |
|------------------------------|---------|-------------------------------|
| `id`                         | string  | 本次请求的唯一标识。                    |
| `object`                     | string  | 响应对象类型，本例为 `chat.completion`。 |
| `model`                      | string  | 实际使用的模型名称。                    |
| `created`                    | integer | 响应创建时间，通常为 Unix 时间戳。          |
| `choices[0].index`           | integer | 当前候选结果的索引，本例为 `0`。            |
| `choices[0].message.role`    | string  | 返回消息的角色，本例为 `assistant`。      |
| `choices[0].message.content` | string  | 符合 Schema 的 JSON 字符串，需要再次解析。  |
| `choices[0].finish_reason`   | string  | 生成结束原因，本例为 `stop`。            |
| `usage`                      | object  | 本次请求的 Token 使用统计。             |

将 `message.content` 解析后，得到的结构化对象为：

```json
{
  "age": 35,
  "name": "张三",
  "occupation": "高级软件工程师",
  "skills": [
    "Python",
    "Java",
    "机器学习"
  ]
}
```

内部字段说明：

| 字段           | 类型              | 作用                  |
|--------------|-----------------|---------------------|
| `age`        | integer         | 人物年龄。               |
| `name`       | string          | 人物姓名。               |
| `occupation` | string          | 职业名称。               |
| `skills`     | array of string | 技能列表，数组中的每个元素都是字符串。 |

客户端读取 `message.content` 后，还需要再次进行 JSON 解析：

```python
import json

person = json.loads(response.choices[0].message.content)
print(person["name"])
```

## 10. 请求参数

下面介绍几个最常用地可选请求参数。它们都放在请求体的顶层，与 `model`、`messages` 和 `stream` 同级。

### temperature

- 类型：`number`
- 是否必填：否
- 取值范围：`0.0`～`2.0`
- 默认值：`1.0`

采样温度，用于控制输出的随机性。值越低，回答通常越稳定、越容易复现；值越高，回答通常越灵活，但也可能更发散。

即当同一个问题问很多次时，`temperature` 较低时模型更倾向于给出相似答案；较高时更可能换一种说法或提供不同思路。需要稳定输出时，通常可以从 `0.2` 或 `0.3` 开始尝试。

```shell
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "system", "content": "你是一个有帮助的助手。"},
      {"role": "user", "content": "用一句话介绍深圳。"}
    ],
    "temperature": 0.2,
    "stream": false
  }'
```

### top_p

- 类型：`number`
- 是否必填：否
- 取值范围：`0.0`～`1.0`
- 默认值：`1.0`

核采样（Nucleus Sampling）阈值，用于限制模型每一步生成时可以考虑的候选词范围。

即模型每次生成下一个词时，可能有很多候选词。`top_p` 会优先保留累计概率达到该阈值的候选词，值越小，候选范围通常越窄，输出也可能越集中；值为 `1.0` 时不额外缩小候选范围。

通常建议只调整 `temperature` 或 `top_p` 其中一个，不要同时调得很激进。

### max_tokens

- 类型：`integer`
- 是否必填：否

限制单次请求允许生成的最大 Token 数。Token 是模型处理文本时使用的基本单位，不完全等同于汉字或单词；这个值越大，模型可生成的内容上限越高，但也可能消耗更多额度。

对于启用思考模式的请求，推理 Token 和最终回答 Token 会共同占用该上限。如果设置过小，模型可能还没有完成思考或回答就提前结束，因此应根据任务复杂度适当调大。

示例：限制模型最多输出约 256 个 Token：

```json
{
  "model": "hy3",
  "messages": [{"role": "user", "content": "用三句话介绍深圳。"}],
  "max_tokens": 256
}
```

### stop

- 类型：`string` 或 `array of string`
- 是否必填：否
- 数量限制：数组最多包含 4 个停止序列

指定一个或多个“遇到后就停止生成”的字符串。模型生成的内容一旦匹配到停止序列，就会立即结束本次生成，并且通常不会把停止序列本身放进返回内容中。

`stop` 就像给模型设置一个“看到这个标记就停笔”的信号。它不是要求模型必须输出这个字符串，而是告诉模型：如果输出过程中遇到了它，就不要继续写。

例如，要求模型输出多行内容，并在遇到 `END` 时停止：

```json
{
  "model": "hy3",
  "messages": [{
    "role": "user",
    "content": "列出三个水果，每行一个。输出完后写 END。"
  }],
  "stop": ["END"]
}
```

也可以只传入一个字符串：

```json
"stop": "END"
```

如果模型生成到 `END`，客户端通常只会收到此前的水果列表，不会收到 `END` 及其后面的内容。需要注意，`stop` 只控制生成何时停止，不能保证模型一定按照提示生成指定格式。

> 其他请求参数如 `n`, `seed` 等可以参考[请求参数](https://cloud.tencent.com/document/product/1823/130079#0f2eb282-746e-4e00-b6db-bb147bedbc77)

## 11. 常见错误与排查
Chat Completions（`/v1/chat/completions`）和 Responses（`/v1/responses`）协议的错误通常返回以下结构。

### 错误结构
```json
{
  "error": {
    "message": "<英文错误描述>",
    "message_zh": "<中文错误描述>",
    "code": "<业务错误码>",
    "type": "<错误类型>",
    "source": "client | gateway | upstream",
    "upstream_code": "<上游错误码，仅上游错误时返回>",
    "upstream_status": 502,
    "request_id": "<请求唯一标识>"
  }
}
```
### 错误字段说明

| 字段                      | 类型               | 作用                                                              |
|-------------------------|------------------|-----------------------------------------------------------------|
| `error.message`         | string           | 英文错误描述，适合记录到日志。                                                 |
| `error.message_zh`      | string           | 中文错误描述，适合直接展示给中文用户。                                             |
| `error.code`            | string 或 integer | TokenHub 业务错误码，用于精确定位问题；限流场景下可能返回数字。                            |
| `error.type`            | string           | 错误类型；鉴权和参数校验等网关拦截错误通常为 `gateway_error`。                         |
| `error.source`          | string           | 错误来源：`client`（请求端）、`gateway`（网关）或 `upstream`（上游服务）；部分错误不会返回该字段。 |
| `error.upstream_code`   | string           | 上游服务原始错误码，仅在 `source` 为 `upstream` 时出现。                         |
| `error.upstream_status` | integer          | 上游服务 HTTP 状态码，仅在上游错误时出现。                                        |
| `error.request_id`      | string           | 本次请求的唯一标识。联系服务方或提交工单时应一并提供。                                     |

### 常见 HTTP 状态码

| HTTP 状态码                | 常见错误码                               | 常见原因和处理方式                                                          |
|-------------------------|-------------------------------------|--------------------------------------------------------------------|
| `400`                   | `400001`、`400002`                   | 请求体格式错误、必填字段缺失或参数取值无效。检查 `model`、`messages` 及参数范围。                 |
| `400`                   | `400003`                            | 输入 Token 超出模型上下文限制。缩短输入、减少历史消息或调整请求内容。                             |
| `400`                   | `400004`、`401006`                   | 模型或服务 ID 不存在，或模型与服务不匹配。确认 `model` 使用正确的服务 ID。                      |
| `400`                   | `400005`、`400006`                   | 当前模型不支持请求的协议、能力或 `response_format`。查看支持范围后调整请求。                    |
| `401`                   | `401001`～`401004`                   | 未携带认证信息、API Key 错误、过期或被禁用。检查 `Authorization: Bearer ...` 和 Key 状态。 |
| `403`                   | `403001`～`403006`                   | 套餐、模型、账号、IP 白名单或工具权限不足。检查 API Key 和服务权限。                           |
| `413`                   | `413001`                            | 请求体过大。减少消息、工具定义或其他请求内容。                                            |
| `429`                   | `429001`～`429005`                   | 超过请求频率、RPM、TPM、TPD 或并发限制。降低频率或并发量。                                 |
| `429`                   | `429006`                            | 模型服务繁忙或达到服务容量上限。等待后再重试。                                            |
| `451`                   | `451001`                            | 输入或输出内容触发安全策略，需要调整请求内容。                                            |
| `500`、`502`、`503`、`504` | `500001`、`502001`、`503001`、`504001` | 平台内部错误、上游异常、服务暂不可用或网关超时。可重试；持续失败时提供 `request_id` 排查。               |

限流响应还可能包含 `Retry-After` 响应头，单位为秒。客户端应同时兼容字符串和数字两种 `error.code` 类型，并优先按照 `Retry-After` 等待后再重试。

### 模型服务繁忙或达到容量上限

当模型服务当前繁忙，或已达到服务容量上限时，网关可能返回 HTTP `429`。实际遇到的响应如下：

```json
{
  "error": {
    "type": "rate_limit_error",
    "code": "429006",
    "message": "The model service is currently busy or has reached its serving capacity limit. Please reduce the request frequency and try again later.",
    "message_zh": "当前模型服务繁忙或已达服务容量上限，请降低请求频率后稍后重试。",
    "source": "gateway",
    "request_id": "57b8d6ff-03dd-45a0-8d8e-5eebba3e0470"
  }
}
```

处理建议：

1. 降低请求频率，避免立即连续重试。
2. 等待一段时间后再发起请求。
3. 在客户端实现带指数退避和随机抖动的重试策略。
4. 检查当前地域、API Key、套餐及模型广场中的 RPM/TPM 限制。
5. 如果持续出现，记录 `request_id`、请求时间和模型名，并联系服务方排查。

该错误通常不表示请求 JSON 格式错误；修改 `messages` 或 `response_format` 一般不能直接解决服务容量不足问题。

更完整的错误码、协议差异和错误响应示例，请参考腾讯云官方文档：[TokenHub API 错误码说明](https://cloud.tencent.com/document/product/1823/131595)。

## 示例与进一步实践

本文中的 curl 示例用于快速理解请求和响应格式；如果需要运行完整的 Python 代码，请阅读 [`examples/README_cn.md`](examples/README_cn.md)。示例目录提供统一的环境变量配置、运行命令和输出说明，每个 Python 文件都有对应的中文 Markdown 文档。

从以下示例开始，可以逐步验证不同 API 能力：

| 场景              | 示例                                                                                | 说明                                        |
|-----------------|-----------------------------------------------------------------------------------|-------------------------------------------|
| 基础对话            | [`01_basic_chat.py`](examples/01_basic_chat.py)                                   | 使用 Chat Completions API 完成最小文本调用。         |
| 流式输出            | [`02_streaming.py`](examples/02_streaming.py)                                     | 逐个读取 Chat Completions 流式 chunk，并获取 usage。 |
| 流式对比            | [`03_streaming_vs_non_streaming.py`](examples/03_streaming_vs_non_streaming.py)   | 对比首 chunk 延迟和完整响应耗时。                      |
| Chat 工具调用       | [`04_tool_calling.py`](examples/04_tool_calling.py)                               | 声明函数工具、执行本地函数并回传工具结果。                     |
| Chat 推理模式       | [`05_reasoning_mode.py`](examples/05_reasoning_mode.py)                           | 对比普通模式与推理模式的响应。                           |
| Responses 基础调用  | [`06_responses_basic.py`](examples/06_responses_basic.py)                         | 使用 Responses API 并读取 `output_text`。       |
| Responses 流式输出  | [`07_responses_streaming.py`](examples/07_responses_streaming.py)                 | 解析 Responses API 的 SSE 事件。                |
| Responses 工具调用  | [`08_responses_tool_calling.py`](examples/08_responses_tool_calling.py)           | 回传 `function_call_output` 并获取最终回答。        |
| Responses 结构化输出 | [`09_responses_structured_output.py`](examples/09_responses_structured_output.py) | 使用 JSON Schema 约束输出并解析 JSON。              |
| 错误处理与重试         | [`10_error_handling_retry.py`](examples/10_error_handling_retry.py)               | 处理超时、网络错误、限流和服务端错误。                       |

从仓库根目录运行示例：

```bash
uv run --env-file .env python examples/01_basic_chat.py
```

示例输出会受到模型版本、随机采样、网络延迟和服务负载影响。示例中的天气函数只返回演示数据，不会访问真实天气服务。

## 参考资料

- [TokenHub 快速入门](https://cloud.tencent.com/document/product/1823/130058)：介绍 TokenHub 控制台和基础使用流程。
- [TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078)：介绍接口域名、鉴权方式、模型列表和异常处理。
- [TokenHub 语言模型调用概览](https://cloud.tencent.com/document/product/1823/130079)：介绍公共请求参数、响应字段、工具调用和流式输出。
- [Hy3 调用指南](https://cloud.tencent.com/document/product/1823/132252)：介绍 Hy3 的模型限制、协议支持和专用调用方式。
- [TokenHub 深度思考](https://cloud.tencent.com/document/product/1823/131208)：介绍 `thinking`、`reasoning_effort` 和推理模式相关参数。
- [TokenHub API 错误码说明](https://cloud.tencent.com/document/product/1823/131595)：介绍 HTTP 状态码、业务错误码和错误排查方式。
- [TokenHub Responses API 兼容模式说明](https://cloud.tencent.com/document/product/1823/133813)：介绍 Responses API 的参数支持范围、输入输出结构和兼容性限制。
- [词汇表](https://cloud.tencent.com/document/product/1823/130120#2897)：解释 TokenHub 文档中的常用术语。

参数是否支持以及具体行为，不能只根据单次响应推断。接入其他模型或更换地域后，应结合模型广场、官方文档和实际接口响应重新验证。
