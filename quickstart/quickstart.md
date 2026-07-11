# Hy3 API Quickstart

## 1 概述

腾讯混元大模型（Tencent Hy）是由腾讯研发的大语言模型，具备强大的中文创作能力、复杂语境下的逻辑推理能力，以及可靠的任务执行能力。

Hy3 API 兼容 OpenAI Chat Completions API 协议，您可以直接使用 OpenAI SDK 或任何兼容客户端接入。

## 2 基础信息

### 2.1 Base URL

`https://tokenhub.tencentmaas.com/v1`

### 2.2 API Key 获取

1. 注册 [腾讯云](https://cloud.tencent.com/document/product/378/17985) 账号
2. 开通 TokenHub 服务
3. 在 [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey) 获取 API Key

### 2.3 支持模型

| model 参数值  | 能力说明                                                                                         | 上下文窗口 | 最大输入 | 最大输出 | QPM |
| ------------- | ------------------------------------------------------------------------------------------------ | ---------- | -------- | -------- | --- |
| `hy3`         | 基于真实业务场景打磨，兼具效果和性价比，强化 Coding、长文、推理和 Agent 等能力                   | 256k       | 192k     | 128k     | 60  |
| `hy3-preview` | 面向 Agent 工作负载设计，采用 MoE 架构，支持交错式思考、结构化输出、Function Calling、Cache 缓存 | 256k       | 192k     | 128k     | 60  |

## 3 最小可运行示例

### 3.1 cURL 示例

```bash
curl -X POST 'https://tokenhub.tencentmaas.com/v1/chat/completions' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好，请简单介绍一下你自己。"}
    ],
    "stream": false,
    "temperature": 0.9
  }'
```

### 3.2 Python OpenAI SDK 示例

```bash
pip install openai python-dotenv
```

```python
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好，请简单介绍一下你自己。"},
    ],
    temperature=0.9,
)

print(response.choices[0].message.content)
```

1. 将以上代码保存为 `quickstart.py`
2. 创建 `.env` 文件并设置 `HY3_API_KEY=your_api_key_here`
3. 执行 `python quickstart.py`

## 4. 核心参数说明

### 4.1 采样参数

| 参数          | 类型         | 范围       | 默认值 | 说明                                          |
| ------------- | ------------ | ---------- | ------ | --------------------------------------------- |
| `temperature` | float        | [0.0, 2.0] | 1.0    | 温度系数，值越高输出越随机                    |
| `top_p`       | float        | [0.0, 1.0] | 1.0    | 核采样概率阈值，建议与 temperature 二选一使用 |
| `max_tokens`  | int          | -          | 16384  | 最大输出 token 数                             |
| `stop`        | string/array | -          | []     | 停止序列，最多 4 个                           |

### 4.2 思考模式参数

| 参数               | 类型   | 说明                                                                  |
| ------------------ | ------ | --------------------------------------------------------------------- |
| `thinking`         | object | 思考模式控制，`{"type": "enabled"}` 开启，`{"type": "disabled"}` 关闭 |
| `reasoning_effort` | string | 推理深度：`low`（轻量）、`medium`（平衡）、`high`（深度）             |

**注意**：在 Python OpenAI SDK 中，`thinking` 和 `reasoning_effort` 需要通过 `extra_body` 参数传递。

### 4.3 工具调用参数

| 参数                  | 类型          | 说明                                                |
| --------------------- | ------------- | --------------------------------------------------- |
| `tools`               | array         | 工具定义列表                                        |
| `tool_choice`         | string/object | 工具调用策略：`none`、`auto`、`required` 或指定工具 |
| `parallel_tool_calls` | bool          | 是否允许并行调用多个工具                            |

## 5. 响应结构解析

### 5.1 非流式响应

```json
{
  "id": "REPLACED_ID",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1775146513,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是混元，是由腾讯开发的大模型。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 22,
    "completion_tokens": 50,
    "total_tokens": 72,
    "prompt_tokens_details": {"cached_tokens": 0},
    "completion_tokens_details": {"reasoning_tokens": 0}
  }
}
```

### 5.2 流式响应

```txt
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"role": "assistant"}}]}
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "你好"}}]}
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "！"}}]}
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [], "usage": {"prompt_tokens": 16, "completion_tokens": 11, "total_tokens": 27}}
data: [DONE]
```

## 6. 常见报错排查

| 错误码 | 错误信息              | 原因                 | 解决方案                        |
| ------ | --------------------- | -------------------- | ------------------------------- |
| 401    | Unauthorized          | API Key 错误或过期   | 检查 API Key 是否正确，重新生成 |
| 403    | Forbidden             | 权限不足或服务未开通 | 确认已开通 TokenHub 服务        |
| 429    | Too Many Requests     | 超过速率限制         | 实现指数退避重试机制            |
| 500    | Internal Server Error | 服务端错误           | 稍后重试                        |
| 400    | Bad Request           | 请求参数格式错误     | 检查 JSON 格式和必填参数        |
| 404    | Not Found             | 模型不存在           | 确认 model 参数值正确           |

## 7. 下一步操作

查看 `examples/` 目录中的示例代码，了解更多使用场景：

1. [basic_chat](examples/01_basic_chat) - 基础对话（单轮/多轮）
2. [streaming](examples/02_streaming) - 流式请求
3. [streaming_comparison](examples/03_streaming_comparison) - 流式 vs 非流式对比
4. [tool_calling](examples/04_tool_calling) - 工具调用
5. [reasoning_mode](examples/05_reasoning_mode) - 思考模式
6. [error_handling](examples/06_error_handling) - 错误处理与重试

每一个样例都包含有说明文档、notebook、单纯python运行文件
！！！注意配置.env文件，样例见.env.example