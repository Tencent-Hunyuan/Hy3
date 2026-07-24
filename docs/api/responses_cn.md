# Hy3 Responses API

本文介绍如何通过腾讯云 TokenHub 调用 Hy3 Responses API，并简要说明它与
[Chat Completions API](../../quickstart_cn.md) 的差异。

Responses API 可以看作 Chat Completions API 的另一种调用接口：它将输入、输出、工具调用和推理结果统一为带有 `type` 的 Item，适合需要工具、多模态输入或更复杂 Agent 流程的应用。OpenAI 官方迁移指南也将 Responses API 定义为 Chat Completions 的演进，并建议新项目优先评估该接口。

## Chat Completions 与 Responses 的简要对比

两种 API 都可以完成普通文本对话，主要区别在于请求和响应的组织方式：

| 对比项   | Chat Completions API             | Responses API                                                          |
|-------|----------------------------------|------------------------------------------------------------------------|
| 请求地址  | `/v1/chat/completions`           | `/v1/responses`                                                        |
| 普通输入  | 使用 `messages` 消息数组               | 使用顶层 `input`，可以是字符串或输入 Item 数组                                         |
| 指令字段  | 通常放在 `messages` 中，角色为 `system`   | 可以单独使用顶层 `instructions`                                                |
| 文本输出  | `choices[0].message.content`     | 通常使用 `response.output_text`                                            |
| 输出结构  | 以 `choices` 为中心                  | 以 `output` Item 数组为中心，可能包含 `message`、`reasoning`、`function_call` 等不同类型 |
| 工具调用  | 使用 `tool_calls` 和 `role: "tool"` | 使用 `function_call` 和 `function_call_output` Item，并通过 `call_id` 关联      |
| 多轮上下文 | 客户端保存并重新传入 `messages`            | 可以手动传入历史 Item；`previous_response_id` 是否真正生效取决于服务端实现，当前实测未恢复上下文         |

迁移时不应只替换 URL。除了将 `messages` 改为 `input`，还需要同步调整响应解析、工具调用、结构化输出和流式事件处理逻辑。只读取普通文本时，最常见的变化是：

```text
choices[0].message.content  →  response.output_text
```

## 1. 基础信息

### 请求地址

广州入口：

```text
https://tokenhub.tencentmaas.com/v1/responses
```

如果 API Key 属于新加坡地域，请使用对应的入口：

```text
https://tokenhub-intl.tencentmaas.com/v1/responses
```

API Key、Base URL 和服务地域必须保持一致。鉴权方式与 Chat Completions 相同：

```http
Authorization: Bearer ${HY3_API_KEY}
```

### 模型名称

本文示例使用 Hy3 的服务 ID：

```text
hy3
```

> 注意：模型广场已明确声明 Hy3 支持 OpenAI Chat Completions、OpenAI Responses 和 Anthropic Messages 协议。
> 腾讯云“Responses API 兼容模式说明”中的模型列表，描述的是兼容模式当前明确列出的模型，不应替代模型广场中的协议支持声明。
> 本文以 Hy3 实际接口响应为示例；接入其他模型前，仍建议通过控制台或 `GET /v1/models` 确认模型 ID 和可用协议。

## 2. 第一次调用

Responses API 的最小请求可以使用顶层 `instructions` 指定行为，使用 `input` 提供用户输入：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "instructions": "你是一个有帮助的助手。",
    "input": "你好",
    "stream": false
  }'
```

### 请求字段

| 字段             | 类型             | 作用                                               |
|----------------|----------------|--------------------------------------------------|
| `model`        | string         | 模型或服务 ID，本例为 `hy3`。                              |
| `instructions` | string 或 array | 对模型行为的高层指令，作用类似 Chat Completions 中的 `system` 消息。 |
| `input`        | string 或 array | 用户输入，可以是简单文本，也可以是带角色和内容的 Item 数组。                |
| `stream`       | boolean        | 是否使用流式输出；`false` 返回完整响应，`true` 返回事件流。            |

### 消息角色和指令遵循

`instructions` 用于向模型提供较高层级的行为指导，例如角色、语气、任务目标和回答要求。与直接放在 `input` 中的用户问题相比，它更适合承载稳定的开发者指令。

前面的请求使用了顶层 `instructions`：

```json
"instructions": "你是一个有帮助的助手。"
```

如果需要把这类指令与用户输入放在同一个 `input` 数组中，也可以写成消息 Item：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": [
      {
        "role": "developer",
        "content": "你是一个有帮助的助手。"
      },
      {
        "role": "user",
        "content": "你好"
      }
    ],
    "stream": false
  }'
```

对应的响应示例：

```json
{
  "id": "30d23e89-48b8-4ea2-8ba3-b52db746d4c8",
  "object": "response",
  "created_at": 1784793769,
  "completed_at": 1784793769,
  "model": "hy3",
  "status": "completed",
  "output": [
    {
      "type": "message",
      "id": "msg_20260723160249hg5j7l8n",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "你好！👋 有什么我可以帮你的吗？"
        }
      ]
    }
  ],
  "output_text": "你好！👋 有什么我可以帮你的吗？",
  "usage": {
    "input_tokens": 22,
    "output_tokens": 12,
    "total_tokens": 34
  },
  "error": null,
  "metadata": null,
  "parallel_tool_calls": null
}
```

这里的 `output_text` 是最终文本的快捷读取字段；如果需要处理工具调用或其他输出类型，则应继续检查 `output` 数组中的 Item。

> 注意：`instructions` 仅适用于当前响应生成请求。如果使用 `previous_response_id` 管理对话状态，之前回合中的 `instructions` 不会自动出现在后续上下文中。当前实测未通过该参数恢复上下文，应使用 `input` 数组显式传入历史消息。

## 3. 响应结构

下面是一次真实的 Hy3 Responses API 响应：

```json
{
  "id": "6996f62f-a9a1-4c00-86a2-a3d392859da5",
  "object": "response",
  "created_at": 1784778399,
  "completed_at": 1784778399,
  "model": "hy3",
  "status": "completed",
  "output": [
    {
      "type": "message",
      "id": "msg_20260723114639qg5i7u8x",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "你好！😊 有什么我可以帮你的吗？"
        }
      ]
    }
  ],
  "output_text": "你好！😊 有什么我可以帮你的吗？",
  "usage": {
    "input_tokens": 22,
    "output_tokens": 12,
    "total_tokens": 34
  },
  "error": null,
  "metadata": null,
  "instructions": "你是一个有帮助的助手。",
  "parallel_tool_calls": null
}
```

### 常用响应字段

| 字段                        | 类型            | 作用                                                  |
|---------------------------|---------------|-----------------------------------------------------|
| `id`                      | string        | 本次响应的唯一标识，可用于日志和问题排查。                               |
| `object`                  | string        | 响应对象类型，本例为 `response`。                              |
| `status`                  | string        | 响应状态，本例为 `completed`。                               |
| `output`                  | array         | 输出 Item 数组。除普通消息外，还可能包含推理或工具调用 Item。                |
| `output[].type`           | string        | Item 类型，例如 `message`、`reasoning` 或 `function_call`。 |
| `output[].content`        | array         | 消息内容数组，本例中的内容类型为 `output_text`。                     |
| `output[].content[].text` | string        | 当前文本内容。                                             |
| `output_text`             | string        | SDK 或服务提供的文本快捷字段，适合只需要最终文本的场景。                      |
| `usage`                   | object        | Token 使用统计。                                         |
| `usage.input_tokens`      | integer       | 输入消耗的 Token 数量。                                     |
| `usage.output_tokens`     | integer       | 输出消耗的 Token 数量。                                     |
| `usage.total_tokens`      | integer       | 输入和输出消耗的 Token 总数。                                  |
| `error`                   | object 或 null | 请求失败时的错误信息；成功时通常为 `null`。                           |

如果应用只需要最终文本，优先读取：

```text
response.output_text
```

如果需要处理工具调用、推理结果或多模态内容，则应遍历 `response.output`，并根据每个 Item 的 `type` 分别处理。不能假设 `output` 中的每个元素都是普通消息。

## 4. Python OpenAI SDK

安装 SDK：

```bash
pip install -U openai
```

调用示例：

```python
import os

from openai import OpenAI


client = OpenAI(
    api_key=os.environ["HY3_API_KEY"],
    base_url=os.getenv(
        "HY3_BASE_URL",
        "https://tokenhub.tencentmaas.com/v1",
    ),
)

response = client.responses.create(
    model="hy3",
    instructions="你是一个有帮助的助手。",
    input="你好，请简单介绍一下 Hy3。",
)

print(response.output_text)
```

如果使用新加坡地域，可以设置：

```bash
export HY3_BASE_URL="https://tokenhub-intl.tencentmaas.com/v1"
```

## 5. 多轮对话的基本思路

### 手动传入历史消息

在 TokenHub Responses API 兼容模式下，多轮对话需要由客户端保存历史，并在下一次请求中通过 `input` 数组完整传入。数组中的消息应按照实际对话顺序排列。

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "instructions": "你是一个有帮助的助手。",
    "input": [
      {
        "role": "user",
        "content": "你好，我是小明。"
      },
      {
        "role": "assistant",
        "content": "小明你好，有什么可以帮你的么。"
      },
      {
        "role": "user",
        "content": "我叫什么？"
      }
    ],
    "stream": false
  }'
```

对应的响应核心文本是：

```text
你刚才告诉我，你叫**小明**。😊
```

请求中的条目类型可参考[Responses API 兼容模式说明](https://cloud.tencent.com/document/product/1823/133813#f4b14c90-1272-4b14-9658-c69c7414bbfa)：

| 条目类型      | `type` 取值                 | 说明                                                       |
|-----------|---------------------------|----------------------------------------------------------|
| 消息        | `message`                 | 标准消息条目，可使用 `user`、`assistant`、`system` 或 `developer` 角色。 |
| 函数调用      | `function_call`           | 表示模型发起的函数调用。                                             |
| 函数调用结果    | `function_call_output`    | 表示工具执行后返回的结果。                                            |
| 推理        | `reasoning`               | 表示上一轮响应中的推理条目。                                           |
| 自定义工具调用   | `custom_tool_call`        | 自定义工具调用条目，处理方式与 `function_call` 类似。                      |
| 自定义工具调用结果 | `custom_tool_call_output` | 自定义工具调用的执行结果，处理方式与 `function_call_output` 类似。            |

以上类型为兼容模式文档列出的常见条目。其他能力（例如计算机操作工具）是否可用，取决于模型和服务端配置，应以官方文档及实际响应为准。

### `previous_response_id` 的实际行为

先发起第一轮请求：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "你好，我是小明",
    "stream": false
  }'
```

第一轮响应的 `id` 为 `b5230f8f-f679-4a48-8e17-034a04785a1d`，响应内容如下：

```json
{
  "id": "b5230f8f-f679-4a48-8e17-034a04785a1d",
  "object": "response",
  "created_at": 1784797027,
  "completed_at": 1784797028,
  "model": "hy3",
  "status": "completed",
  "output_text": "你好呀，小明！很高兴认识你 😊 有什么我可以帮你的吗？",
  "usage": {
    "input_tokens": 19,
    "output_tokens": 18,
    "total_tokens": 37
  }
}
```

将第一轮响应的 `id` 作为 `previous_response_id`，发起第二轮请求：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "我叫什么？",
    "previous_response_id": "b5230f8f-f679-4a48-8e17-034a04785a1d",
    "stream": false
  }'
```

第二轮响应仍然未能识别第一轮中的“小明”：

```json
{
  "id": "37d467fc-4682-47d2-909c-d4291c4027f8",
  "object": "response",
  "created_at": 1784797050,
  "completed_at": 1784797051,
  "model": "hy3",
  "status": "completed",
  "output_text": "哈哈，你还没告诉过我你的名字呢～ 要不现在告诉我？😊",
  "usage": {
    "input_tokens": 18,
    "output_tokens": 19,
    "total_tokens": 37
  }
}
```

该结果表明：当前接口可以接受 `previous_response_id` 字段，但本次调用未通过该字段恢复第一轮上下文。字段名本身没有问题，问题在于当前服务路径下的状态续接能力尚未生效。因此，多轮对话应通过 `input` 数组显式传入完整历史消息，并以实际响应验证服务端是否支持其他状态管理参数。

## 6. 思考模式

Responses API 与 Chat Completions API 的思考参数写法不同：

- Chat Completions API 使用 `thinking`，例如 `{"thinking": {"type": "enabled"}}`。
- Responses API 使用 `reasoning.effort`，例如 `{"reasoning": {"effort": "high"}}`。

因此，下面这种写法属于 Chat Completions 风格，不能作为 Responses API 开启思考模式的依据：

```json
"thinking": {"type": "enabled"}
```

Responses API 可以使用以下请求测试推理能力：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "请计算 37 × 24，并用一句话说明结果。",
    "reasoning": {
      "effort": "high"
    },
    "stream": false
  }'
```

实际响应如下。为避免在介绍文档中直接展示模型的完整内部推理文本，下面仅保留 `reasoning` 条目的结构，并对摘要内容进行省略：

```json
{
  "id": "e537ec27-d4f5-48c0-874d-51e3ed60d38b",
  "object": "response",
  "created_at": 1784800455,
  "completed_at": 1784800472,
  "model": "hy3",
  "status": "completed",
  "output": [
    {
      "type": "reasoning",
      "id": "rs_20260723175432n5s7v8xb",
      "status": "completed",
      "summary": [
        {
          "type": "summary_text",
          "text": "（推理摘要内容已省略）"
        }
      ]
    },
    {
      "type": "message",
      "id": "msg_20260723175432zxkzd0f3",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "37 × 24 的计算过程为 37 × (20 + 4) = 740 + 148 = 888。\n\n37与24相乘的最终结果为888。"
        }
      ]
    }
  ],
  "output_text": "37 × 24 的计算过程为 37 × (20 + 4) = 740 + 148 = 888。\n\n37与24相乘的最终结果为888。",
  "usage": {
    "input_tokens": 24,
    "output_tokens": 1083,
    "total_tokens": 1107,
    "output_tokens_details": {
      "reasoning_tokens": 1045
    }
  },
  "error": null,
  "metadata": null,
  "parallel_tool_calls": null,
  "reasoning": {}
}
```

从该响应可以确认思考模式已经生效：

- `output` 中包含一个 `type: "reasoning"` 的推理条目。
- `output` 中还包含最终的 `message` 条目，应用通常从 `output_text` 读取最终文本。
- `usage.output_tokens_details.reasoning_tokens` 为 `1045`，表示本次响应使用了推理 Token。
- `output_tokens` 包含推理 Token 和最终回答 Token，因此总 Token 消耗为 `1107`。

`reasoning.effort` 用于设置推理投入程度，具体可用取值应以模型和 TokenHub 服务支持为准。关闭推理时，兼容模式文档示例使用 `none` 或 `no_think`：

```json
"reasoning": {"effort": "none"}
```

开启思考模式并不代表服务会返回完整的原始思维链。应用通常应读取 `output_text`；如果服务返回 `reasoning` 输出条目或 `usage.output_tokens_details.reasoning_tokens`，可以据此判断响应中是否包含推理相关信息，但不应默认展示模型的内部推理过程。

> 注意：如果请求携带 `thinking` 后仍然返回正常结果，不能据此证明思考模式已经开启；该字段可能被服务接受但忽略。应优先使用 `reasoning.effort`，并结合实际 `output` 和 `usage` 响应验证。

## 7. 工具调用

Responses API 的工具调用通常分为四个阶段：声明工具、解析模型返回的工具调用、在应用侧执行工具，以及将执行结果回传给模型。模型只负责决定是否调用工具并生成参数，实际的 `get_weather` 函数需要由应用程序自行实现。

与 Chat Completions API 相比，Responses API 的函数工具定义采用扁平结构：`type`、`name`、`description` 和 `parameters` 直接位于工具对象中，不再嵌套在 `function` 字段下。

### 7.1 声明工具并发起请求

下面的请求声明了一个 `get_weather` 函数，并允许模型自动决定是否调用该函数：
```shell
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "深圳今天天气怎么样？",
    "tools": [
      {
        "type": "function",
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
          "required": ["city"],
          "additionalProperties": false
        }
      }
    ],
    "tool_choice": "auto",
    "stream": false
  }'
```

其中：

- `tools` 是工具列表。每个工具的 `type` 为 `function`，`name` 是函数名，`description` 用于说明函数用途，`parameters` 使用 JSON Schema 描述函数参数。
- `parameters.type` 为 `object`，表示函数参数是一个 JSON 对象。
- `properties` 定义可用参数。示例中的 `city` 类型为 `string`，表示城市名称是字符串。
- `required` 指定必填参数。示例中 `city` 必须由模型提供。
- `additionalProperties: false` 表示参数对象不应包含 Schema 未声明的其他字段，有助于限制参数格式。
- `tool_choice: "auto"` 表示由模型自动判断是否调用工具。

### 7.2 解析模型返回的工具调用

本次请求的实际响应如下：
```json
{
  "id": "52eaea93-d218-4b7f-bb57-2dd80f63f363",
  "object": "response",
  "created_at": 1784801451,
  "completed_at": 1784801452,
  "model": "hy3",
  "status": "completed",
  "output": [
    {
      "type": "function_call",
      "id": "fc_20260723181052fzd0f2g4",
      "status": "completed",
      "name": "get_weather",
      "call_id": "chatcmpl-tool-7c18a1a4196244d281a75040577e0583",
      "arguments": "{\"city\": \"深圳\"}"
    }
  ],
  "usage": {
    "input_tokens": 213,
    "output_tokens": 20,
    "total_tokens": 233,
    "tool_usage": {
      "function_call": 1
    }
  },
  "error": null,
  "metadata": null,
  "tools": [
    {
      "type": "function",
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
        "required": ["city"],
        "additionalProperties": false
      }
    }
  ],
  "parallel_tool_calls": null,
  "tool_choice": "auto"
}
```

当 `output` 中出现 `type: "function_call"` 时，应用应读取以下字段：

- `name`：需要调用的函数名，本例为 `get_weather`。
- `arguments`：函数参数。该字段是 JSON 字符串，应用需要先解析，再传递给实际函数。
- `call_id`：本次工具调用的关联 ID。回传工具结果时，`function_call_output.call_id` 必须与它完全一致。
- `id`：工具调用输出项自身的 ID，用于标识该输出项。

### 7.3 执行工具并回传结果

应用解析 `arguments` 后调用本地的 `get_weather` 函数。假设函数返回深圳天气为晴天、气温为 28℃，则将结果作为 `function_call_output` 回传。工具结果由应用生成，下面的 JSON 仅表示回传格式：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": [
      {
        "role": "user",
        "content": "深圳今天天气怎么样？"
      },
      {
        "type": "function_call",
        "id": "fc_20260723181052fzd0f2g4",
        "status": "completed",
        "name": "get_weather",
        "call_id": "chatcmpl-tool-7c18a1a4196244d281a75040577e0583",
        "arguments": "{\"city\":\"深圳\"}"
      },
      {
        "type": "function_call_output",
        "call_id": "chatcmpl-tool-7c18a1a4196244d281a75040577e0583",
        "output": "{\"city\":\"深圳\",\"weather\":\"晴\",\"temperature\":28}"
      }
    ],
    "tools": [
      {
        "type": "function",
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
          "required": ["city"],
          "additionalProperties": false
        }
      }
    ],
    "tool_choice": "auto",
    "stream": false
  }'
```

回传时需要注意：

- `function_call` 条目应保留在 `input` 中，以便模型了解之前发起的工具调用。
- `function_call_output.call_id` 必须对应第一轮响应中的 `call_id`，不能使用 `id` 替代。
- `function_call_output.output` 通常应传入 JSON 字符串，其中可以包含工具执行结果，也可以包含错误信息。
- 第二次请求仍需提供 `tools` 定义，以便模型继续处理工具结果。

### 7.4 读取最终回答

回传工具结果后，接口会返回最终回答。本次调用的实际响应如下：
```json
{
  "id": "256f0a6d-9848-4ebb-9b1d-82d8056448cc",
  "object": "response",
  "created_at": 1784801741,
  "completed_at": 1784801742,
  "model": "hy3",
  "status": "completed",
  "output": [
    {
      "type": "message",
      "id": "msg_20260723181542q4u7wjym",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "深圳今天的天气是**晴天**，当前气温为 **28℃**。"
        }
      ]
    }
  ],
  "output_text": "深圳今天的天气是**晴天**，当前气温为 **28℃**。",
  "usage": {
    "input_tokens": 256,
    "output_tokens": 15,
    "total_tokens": 271
  },
  "error": null,
  "metadata": null,
  "tools": [
    {
      "type": "function",
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
        "required": ["city"],
        "additionalProperties": false
      }
    }
  ],
  "parallel_tool_calls": null,
  "tool_choice": "auto"
}
```

应用通常直接读取 `output_text` 获取最终文本；如果响应中仍然返回 `function_call`，则应继续执行对应工具并重复回传步骤，直到获得 `message` 类型的最终回答。一次响应也可能包含多个工具调用，此时应分别执行这些调用，并将每个结果都作为对应的 `function_call_output` 回传。

本文仅展示 `function` 类型工具。文件搜索、网络搜索等其他工具是否可用，取决于模型和服务端的实际支持情况，使用前应参考模型广场、接口文档及实际响应。

## 8. 流式输出

将请求体中的 `stream` 设置为 `true`，即可通过 Server-Sent Events（SSE）接收流式响应。与非流式请求一次返回完整 JSON 不同，流式响应会将生成过程拆分为多个事件逐步发送。

```bash
curl -N -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "instructions": "你是一个有帮助的助手。",
    "input": "你好",
    "stream": true
  }'
```

响应示例：

本次请求的实际响应如下：

```text
event: response.created
data: {"type":"response.created","response":{"id":"e8c19a9b-3ac4-466a-8e42-2f186a745f54","object":"response","created_at":1784798756,"model":"hy3","status":"in_progress","output":null,"error":null,"metadata":null,"parallel_tool_calls":null}}

event: response.in_progress
data: {"type":"response.in_progress","response":{"id":"e8c19a9b-3ac4-466a-8e42-2f186a745f54","object":"response","created_at":1784798756,"model":"hy3","status":"in_progress","output":null,"error":null,"metadata":null,"parallel_tool_calls":null}}

event: response.output_item.added
data: {"type":"response.output_item.added","output_index":0,"item":{"type":"message","id":"msg_20260723172557g2xi5pb3","status":"in_progress","role":"assistant","content":[]}}

event: response.content_part.added
data: {"type":"response.content_part.added","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"part":{"type":"output_text"}}

event: response.output_text.delta
data: {"type":"response.output_text.delta","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"delta":"你好"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"delta":"！"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"delta":"👋 "}

event: response.output_text.delta
data: {"type":"response.output_text.delta","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"delta":"有什么我可以"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"delta":"帮你的"}

event: response.output_text.delta
data: {"type":"response.output_text.delta","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"delta":"吗？"}

event: response.output_text.done
data: {"type":"response.output_text.done","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"text":"你好！👋 有什么我可以帮你的吗？"}

event: response.content_part.done
data: {"type":"response.content_part.done","output_index":0,"item_id":"msg_20260723172557g2xi5pb3","content_index":0,"part":{"type":"output_text","text":"你好！👋 有什么我可以帮你的吗？"}}

event: response.output_item.done
data: {"type":"response.output_item.done","output_index":0,"item":{"type":"message","id":"msg_20260723172557g2xi5pb3","status":"completed","role":"assistant","content":[{"type":"output_text","text":"你好！👋 有什么我可以帮你的吗？"}]}}

event: response.completed
data: {"type":"response.completed","response":{"id":"e8c19a9b-3ac4-466a-8e42-2f186a745f54","object":"response","created_at":1784798756,"completed_at":1784798757,"model":"hy3","status":"completed","output":[{"type":"message","id":"msg_20260723172557g2xi5pb3","status":"completed","role":"assistant","content":[{"type":"output_text","text":"你好！👋 有什么我可以帮你的吗？"}]}],"usage":{"input_tokens":22,"output_tokens":12,"total_tokens":34},"error":null,"metadata":null,"instructions":"你是一个有帮助的助手。","parallel_tool_calls":null}}
```

每个事件通常由两行组成：

```text
event: <事件名称>
data: <JSON 数据>
```

常用事件如下：

| 事件                           | 作用                               |
|------------------------------|----------------------------------|
| `response.created`           | 创建响应对象，返回响应 ID。                  |
| `response.in_progress`       | 表示响应正在生成。                        |
| `response.output_item.added` | 新增一个输出 Item，例如 assistant 消息。     |
| `response.output_text.delta` | 返回一段增量文本，应按顺序拼接 `delta`。         |
| `response.output_text.done`  | 当前文本输出完成，并提供完整文本。                |
| `response.output_item.done`  | 当前输出 Item 完成。                    |
| `response.completed`         | 整个响应完成；通常可以在该事件中读取完整响应和 `usage`。 |

需要注意：并不是每个事件都包含 `delta`，解析器应先判断事件类型，再读取对应字段。Responses API 的流式响应以事件类型区分状态和内容，不应直接复用 Chat Completions 的 chunk 解析逻辑。当前 Hy3 实际返回的完整事件序列可参考[Responses API 兼容模式说明](https://cloud.tencent.com/document/product/1823/133813#9c486a9a-fbf7-4a2a-ad58-866483d605d7)。

## 9. 结构化输出

结构化输出用于要求模型按照指定的 JSON Schema 返回结果，适合人物信息抽取、分类、实体识别等场景。它约束的是模型最终生成的文本格式，不等同于工具调用：模型不会执行函数，而是直接生成符合 Schema 的 JSON 文本。

### 9.1 请求示例

下面的请求要求模型从文本中提取人物信息，并按照 `person_info` Schema 返回 JSON：

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "提取以下文本中的人物信息：张三，男，25岁，北京人。",
    "text": {
      "format": {
        "type": "json_schema",
        "name": "person_info",
        "schema": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "gender": {"type": "string"},
            "age": {"type": "number"},
            "city": {"type": "string"}
          },
          "required": ["name", "gender", "age", "city"],
          "additionalProperties": false
        },
        "strict": true
      }
    }
  }'
```

请求中的关键字段如下：

- `text`：Responses API 的文本输出配置对象。
- `text.format`：指定文本输出格式。
- `text.format.type`：设置为 `json_schema`，表示使用 JSON Schema 约束输出。
- `text.format.name`：Schema 名称，本例为 `person_info`，用于标识该输出结构。
- `text.format.schema`：具体的 JSON Schema，描述输出对象的字段、类型和必填项。
- `properties`：声明允许返回的字段。本例包含 `name`、`gender`、`age` 和 `city`。
- `required`：声明必填字段，模型应返回数组中的全部字段。
- `additionalProperties: false`：不允许返回 Schema 中未声明的字段。
- `strict: true`：要求服务严格按照 Schema 生成结构化结果；实际可用性仍应以模型和服务端支持情况为准。

### 9.2 实际响应

本次请求的实际响应如下：

```json
{
  "id": "a96b126e-9ab0-4081-a05e-9ecb2d952876",
  "object": "response",
  "created_at": 1784802698,
  "completed_at": 1784802699,
  "model": "hy3",
  "status": "completed",
  "output": [
    {
      "type": "message",
      "id": "msg_20260723183139eocqe2g4",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "{\"age\": 25, \"city\": \"北京\", \"gender\": \"男\", \"name\": \"张三\"}"
        }
      ]
    }
  ],
  "output_text": "{\"age\": 25, \"city\": \"北京\", \"gender\": \"男\", \"name\": \"张三\"}",
  "usage": {
    "input_tokens": 31,
    "output_tokens": 25,
    "total_tokens": 56
  },
  "error": null,
  "metadata": null,
  "parallel_tool_calls": null,
  "text": {
    "format": {
      "type": "json_schema",
      "name": "person_info",
      "schema": {
        "additionalProperties": false,
        "properties": {
          "age": {
            "type": "number"
          },
          "city": {
            "type": "string"
          },
          "gender": {
            "type": "string"
          },
          "name": {
            "type": "string"
          }
        },
        "required": [
          "name",
          "gender",
          "age",
          "city"
        ],
        "type": "object"
      },
      "strict": true
    }
  }
}
```

响应中的 `output` 仍然是 Responses API 的标准输出 Item 数组，文本内容位于 `output[0].content[0].text`。为了方便只读取最终文本，也可以使用 `output_text`。这两个字段的值都是字符串，字符串内容本身是符合 Schema 的 JSON，因此应用通常需要再进行一次 JSON 解析：

```python
import json

person = json.loads(response.output_text)
print(person["name"])
print(person["age"])
```

解析后得到的对象类似于：

```json
{
  "age": 25,
  "city": "北京",
  "gender": "男",
  "name": "张三"
}
```

需要注意，`output_text` 不是已经解析好的 Python 字典或 JavaScript 对象，而是包含 JSON 文本的字符串。生产环境中应在解析前处理请求失败、响应为空和 JSON 格式异常等情况。

## 10. 请求参数

Responses API 的部分请求参数与 Chat Completions API 的含义相近，但字段名称和服务端支持范围可能不同。以下参数适合在确认模型支持后使用：

| 参数                  | 类型                 | 作用                                                                                           |
|---------------------|--------------------|----------------------------------------------------------------------------------------------|
| `temperature`       | Float              | 控制输出随机性。数值越低，输出通常越稳定；数值越高，输出通常越灵活。                                                           |
| `top_p`             | Float              | 控制核采样范围。数值越低，模型考虑的候选词范围通常越小。一般建议优先调整 `temperature` 或 `top_p` 其中一个。                           |
| `max_output_tokens` | Integer            | 限制模型最多生成的输出 Token 数量。Responses API 通常使用该字段；不要直接将 Chat Completions API 的 `max_tokens` 机械复制过来。 |
| `stop`              | string 或 string 数组 | 标准 Responses API 中用于指定停止序列；当前 Hy3 Responses API 实测请求可以返回成功，但停止序列未生效，暂不建议依赖该参数。               |
| `tools`             | array              | 声明模型可以调用的工具，例如 `function` 类型工具。工具调用的完整流程见[工具调用](#7-工具调用)。                                    |
| `tool_choice`       | string 或 object    | 控制工具调用策略，例如 `auto` 表示由模型自动决定是否调用工具。                                                          |
| `reasoning`         | object             | 配置 Responses API 的推理能力，例如 `{"effort": "high"}`；是否可用取决于模型和服务端。                                |
| `stream`            | boolean            | 是否以 SSE 事件流返回结果。`false` 返回完整响应，`true` 返回流式事件。                                                |

参数的具体取值范围、默认值和模型限制，应以 [TokenHub Responses API 兼容模式说明](https://cloud.tencent.com/document/product/1823/133813) 及 Hy3 实际接口响应为准。不同模型可能只支持其中一部分参数；即使服务端接受某个字段，也不代表该字段一定会对模型输出产生效果。

### `stop` 参数的实际行为

TokenHub Responses API 兼容模式的参数列表未将 `stop` 列为完全支持的参数。对 Hy3 发起以下测试请求时，接口返回 HTTP `200 OK`，但响应文本仍然包含停止序列 `STOP`：

```bash
curl -i -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "请输出以下内容，并在最后单独输出 STOP：第一行，第二行。",
    "stop": ["STOP"],
    "stream": false
  }'
```

实际响应的核心内容如下：

```json
{
  "id": "e1ef88df-07b4-4a78-bd42-24b9d5cf7474",
  "object": "response",
  "created_at": 1784806181,
  "completed_at": 1784806182,
  "model": "hy3",
  "status": "completed",
  "output": [
    {
      "type": "message",
      "id": "msg_20260723192942i9xctap5",
      "status": "completed",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "第一行\n第二行\nSTOP"
        }
      ]
    }
  ],
  "output_text": "第一行\n第二行\nSTOP",
  "usage": {
    "input_tokens": 30,
    "output_tokens": 7,
    "total_tokens": 37
  },
  "error": null,
  "metadata": null,
  "parallel_tool_calls": null
}
```

该结果表明：当前服务接受了 `stop` 字段，但没有按照预期截断输出。
应用不应依赖 Responses API 中的 `stop` 实现停止生成；如果必须控制输出结构，可以优先使用结构化输出，或在客户端收到完整响应后自行清理指定标记。
该行为可能随模型或服务端版本变化，使用其他模型时应重新验证。

## 11. 常见错误

Responses API 和 Chat Completions API 通常使用相同的错误对象结构。请求失败时，应优先读取 `error.code`、`error.type`、`error.message_zh` 和 `error.request_id`，再根据 HTTP 状态码决定是修改请求、等待重试还是联系服务方排查。

### 错误响应结构

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

常见字段说明：

| 字段                 | 类型               | 作用                                       |
|--------------------|------------------|------------------------------------------|
| `error.type`       | string           | 错误类别，例如参数错误或限流错误。                        |
| `error.code`       | string 或 integer | TokenHub 业务错误码，用于进一步定位问题。                |
| `error.message`    | string           | 英文错误描述，适合写入日志。                           |
| `error.message_zh` | string           | 中文错误描述，适合展示给中文用户。                        |
| `error.source`     | string           | 错误来源，例如 `client`、`gateway` 或 `upstream`。 |
| `error.request_id` | string           | 本次请求的唯一标识。提交工单或反馈问题时应一并提供。               |

### 模型服务繁忙或达到容量上限

当模型服务繁忙或达到服务容量上限时，接口可能返回 HTTP `429` 和业务错误码 `429006`。实际响应示例如下：

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

该错误通常不表示请求 JSON 格式错误，修改 `input` 或 `text.format` 一般不能直接解决服务容量不足问题。可以先降低请求频率或并发量，等待一段时间后重试；如果服务返回 `Retry-After` 响应头，应优先按照该值等待。持续失败时，应记录 `request_id`、请求时间和模型名称，并联系服务方排查。

更多错误码、HTTP 状态码和处理建议，请参考腾讯云官方文档：[TokenHub API 错误码说明](https://cloud.tencent.com/document/product/1823/131595)。

## 12. 注意事项

- Responses API 的工具调用、结构化输出和流式响应字段与 Chat Completions 不完全相同，不能直接复用原有解析器。
- 如果只处理普通文本，可以使用 `response.output_text`；如果需要工具或推理能力，应遍历 `response.output`。
- 不要把 API Key 写入 Python 文件、Shell 脚本或 Markdown 示例，也不要提交 `.env` 文件。
- Hy3 托管 API 的具体参数和能力以模型广场、TokenHub 文档和实际接口响应为准。

参考文档：

- [TokenHub Responses API 兼容模式说明](https://cloud.tencent.com/document/product/1823/133813#9c713665-4bc2-47e5-9cf4-6e77ab45ea45)
- [TokenHub 语言模型调用概览](https://cloud.tencent.com/document/product/1823/130079)
- [TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078)
