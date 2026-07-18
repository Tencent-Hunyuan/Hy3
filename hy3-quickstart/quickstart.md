# Hy3 API Quickstart

> 面向开发者:5 分钟跑通第一次调用,半小时上手 Hy3 主要能力。
> 所有示例输出均为**真实运行结果**(腾讯混元 Hy3,腾讯云 tokenhub,OpenAI 兼容接口)。

Hy3 是腾讯混元的大语言模型,对外提供 **OpenAI Chat Completions 兼容接口**。你现有的 openai SDK / 任意 HTTP 客户端,改 `base_url` + `model` 即可接入。

---

## 1. 基础信息

| 项 | 值 |
|----|----|
| Base URL | `https://tokenhub.tencentmaas.com/v1` |
| 鉴权 | `Authorization: Bearer <YOUR_API_KEY>` |
| Model 名 | `hy3` |
| 核心端点 | `POST /chat/completions` |
| 协议 | OpenAI Chat Completions 兼容(+ `reasoning_content` 思考字段) |
| API Key 获取 | tokenhub 控制台「API Key 管理」:<https://tokenhub.tencentmaas.com> |

> **速率限制**:RPM / TPM / 并发上限以 tokenhub 控制台「在线推理服务」的配额为准(不同服务等级不同)。触发限流会返回 `429`,处理方式见 [example 06](examples/06_error_handling_retry.md)。

---

## 2. 最小可运行示例

### curl

```bash
curl -X POST 'https://tokenhub.tencentmaas.com/v1/chat/completions' \
  -H 'Authorization: Bearer $HY3_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "你好"}
    ]
  }'
```

**真实响应**:

```json
{
  "id": "206ec264-5bad-4d5b-9f94-53e7e290a447",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1784391100,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！有什么我可以帮你的吗？😊"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 22,
    "completion_tokens": 11,
    "total_tokens": 33,
    "completion_tokens_details": { "reasoning_tokens": 0 }
  }
}
```

### Python(openai SDK)

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",                 # 建议从环境变量读取, 切勿硬编码
    base_url="https://tokenhub.tencentmaas.com/v1",
)
resp = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "你好"}],
)
print(resp.choices[0].message.content)
# 你好！有什么我可以帮你的吗？😊
```

**响应解析要点**:
- `choices[0].message.content` —— 模型回答正文
- `choices[0].finish_reason` —— `stop`(正常结束)/ `length`(达 max_tokens)/ `tool_calls`(要调工具)
- `usage.completion_tokens_details.reasoning_tokens` —— 思考消耗的 token(简单问题为 0,推理题 > 0)
- `choices[0].message.reasoning_content` —— **思考过程原文**(仅推理时出现,见 [example 05](examples/05_reasoning_mode.md))

---

## 3. 参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `model` | string | 固定 `hy3` |
| `messages` | array | 对话历史,`{role, content}`,role ∈ `system`/`user`/`assistant`/`tool` |
| `temperature` | float | 0~2,越高越发散;事实/JSON 场景建议 0~0.3 |
| `top_p` | float | 0~1,核采样,与 temperature 二选一调节 |
| `max_tokens` | int | 回答上限(含思考 token)。结构化长输出建议 ≥ 4096 |
| `stop` | array | 停止序列,命中即结束 |
| `tools` | array | Function Calling 工具定义(OpenAI 格式),见 [example 04](examples/04_tool_calling.md) |
| `stream` | bool | `true` 开启 SSE 流式,见 [example 02](examples/02_streaming.md) |
| `reasoning_effort` | string | **思考模式开关**:`low` / `high`(Hy3 特有,经 `extra_body` 透传)。难题开 `high` 走深度推理,简单任务 `low` 更快 |

> OpenAI SDK 未声明 `reasoning_effort` 字段,Python 里需用 `extra_body={"reasoning_effort": "high"}` 透传。

---

## 4. 常见报错排查

| 现象 | 原因 | 处理 |
|------|------|------|
| HTTP 400 `code: 400004` `model or service ID ... does not exist` | model 名写错 / 服务未开通 | 核对 model=`hy3`,确认 tokenhub 已开通在线推理服务 |
| HTTP 401 `Unauthorized` | API Key 缺失/失效/拼错 | 检查 `Authorization: Bearer <key>`,到控制台重新生成 |
| HTTP 429 `Rate limit` | 触发 RPM/TPM 限流 | 退避重试(见 [example 06](examples/06_error_handling_retry.md)),或提升配额 |
| HTTP 5xx / 连接超时 | 网关抖动 | 指数退避重试 |
| 回答被截断 | `finish_reason: length` | 调大 `max_tokens` |
| SDK 报参数不被接受 | 传了非标准字段(如 `reasoning_effort`) | 用 `extra_body={...}` 透传 |

**真实错误响应示例**(非法 model):

```json
{
  "error": {
    "type": "gateway_error",
    "code": "400004",
    "message": "The model or service ID not-a-real-model does not exist...",
    "message_zh": "请求中的模型或服务 ID not-a-real-model 不存在,请检查服务 ID 是否正确。",
    "request_id": "aced97d2-4fc6-401f-b363-95ed89b6f20c"
  }
}
```

> `request_id` 在排查时一并提供给 tokenhub,便于定位。

---

## 5. 进阶 examples

| # | 主题 | 文件 |
|---|------|------|
| 01 | basic chat(单轮 / 多轮) | [examples/01_basic_chat.md](examples/01_basic_chat.md) |
| 02 | streaming(流式 + 逐 chunk 解析) | [examples/02_streaming.md](examples/02_streaming.md) |
| 03 | non-streaming vs streaming(首 token 时延 / 总耗时) | [examples/03_streaming_vs_nonstream.md](examples/03_streaming_vs_nonstream.md) |
| 04 | tool calling(一次调用 + 多轮工具循环) | [examples/04_tool_calling.md](examples/04_tool_calling.md) |
| 05 | reasoning mode(思考过程 开/关 对比) | [examples/05_reasoning_mode.md](examples/05_reasoning_mode.md) |
| 06 | error handling & retry(超时 / 限流 / 网络错误) | [examples/06_error_handling_retry.md](examples/06_error_handling_retry.md) |

可运行脚本见 `examples/*.py`(配合根目录 `.env` 的 `HY3_API_KEY`)。
