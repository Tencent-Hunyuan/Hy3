# Hy3 API 快速开始

本指南使用 Hy3 自部署服务提供的 OpenAI 兼容 API。完成[服务部署](../README_CN.md#推理和部署)后，5 分钟内即可发出第一次请求。

## 1. 基础信息

| 配置 | 本地默认值 | 说明 |
|---|---|---|
| Base URL | `http://127.0.0.1:8000/v1` | vLLM 或 SGLang 的 OpenAI 兼容地址，必须包含 `/v1` |
| API Key | `EMPTY` | 本地服务默认不校验；生产环境应在网关配置真实密钥 |
| Model | `hy3` | 必须与服务启动参数 `--served-model-name` 一致 |
| Chat endpoint | `/chat/completions` | 完整地址为 `${HY3_BASE_URL}/chat/completions` |

Hy3 仓库不提供托管 API，因此没有统一的官方速率限制。自部署服务的并发数、排队长度和网关策略决定实际限制；超过限制时通常返回 HTTP `429`。生产环境应向服务管理员确认配额，并按响应中的 `Retry-After` 退避。

## 2. 准备环境

需要 Python 3.10 或更高版本，以及已经运行的 Hy3 服务。

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements-api.txt

export HY3_BASE_URL=http://127.0.0.1:8000/v1
export HY3_API_KEY=EMPTY
export HY3_MODEL=hy3
```

不要把生产 API Key 写进源码或提交到 Git。可从 [`.env.example`](../.env.example) 查看变量名。

## 3. 第一次调用

### curl

```bash
curl --fail-with-body "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "你好，请用一句话介绍 Hy3。"}],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

响应采用 OpenAI Chat Completions 格式：

```json
{
  "id": "chatcmpl-8d3f",
  "object": "chat.completion",
  "created": 1783824000,
  "model": "hy3",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hy3 是腾讯混元开源的高性能大语言模型。"},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 15, "completion_tokens": 19, "total_tokens": 34}
}
```

读取文本用 `choices[0].message.content`，结束原因用 `choices[0].finish_reason`，token 用量在 `usage` 中。

### Python OpenAI SDK

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
)
response = client.chat.completions.create(
    model=os.getenv("HY3_MODEL", "hy3"),
    messages=[{"role": "user", "content": "你好，请用一句话介绍 Hy3。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

choice = response.choices[0]
print(choice.message.content)
print("finish_reason:", choice.finish_reason)
print("usage:", response.usage)
```

> curl 的扩展字段直接放在 JSON 顶层；OpenAI Python SDK 使用 `extra_body` 传递同一字段。

## 4. 常用参数

| 参数 | 作用 | 建议 |
|---|---|---|
| `temperature` | 控制采样随机性，越低越稳定 | Hy3 推荐 `0.9`；确定性任务可适当降低 |
| `top_p` | 只从累计概率达到阈值的 token 中采样 | Hy3 推荐 `1.0`；通常只调整它和 `temperature` 之一 |
| `max_tokens` | 本次最多生成的 token 数 | 结合任务、上下文窗口和服务限制设置 |
| `stop` | 遇到字符串即停止，可传一个字符串或字符串列表 | 仅在业务有明确终止符时设置 |
| `tools` | JSON Schema 描述的函数工具列表 | 模型只生成调用意图，应用必须执行工具并回传结果 |
| `tool_choice` | `auto`、`none` 或指定函数 | 通常使用 `auto` |
| `stream` | 是否返回 SSE 流 | 交互场景使用 `true` 降低首 token 等待时间 |

### 思考模式

通过 `chat_template_kwargs.reasoning_effort` 控制：

- `no_think`：直接回答，适合日常对话。
- `low`：较短推理。
- `high`：深度推理，适合数学、编程和复杂分析。

```python
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}
```

启用推理解析器后，服务可能在 `message.reasoning_content`（流式时为 `delta.reasoning_content`）返回推理字段。不同后端或版本的返回方式可能不同，业务代码应允许该字段缺失。推理内容可能显著增加生成 token 与延迟。

## 5. 接下来运行示例

```bash
python api/examples/01_basic_chat/basic_chat.py
python api/examples/02_streaming/streaming.py
python api/examples/03_latency_comparison/latency_comparison.py
python api/examples/04_tool_calling/tool_calling.py
python api/examples/05_reasoning_mode/reasoning_mode.py
python api/examples/06_error_handling_retry/error_handling_retry.py
```

每个示例的完整请求、解析逻辑和示例输出见 [examples/README.md](examples/README.md)。

## 6. 常见错误

| 状态/现象 | 常见原因 | 排查方法 |
|---|---|---|
| 连接被拒绝 | 服务未启动、端口错误 | 检查服务日志及 `curl "$HY3_BASE_URL/models"` |
| `401` / `403` | API Key 缺失或网关拒绝 | 检查 `Authorization: Bearer ...`，不要在日志中打印密钥 |
| `404` | Base URL 缺少 `/v1`、模型名错误 | 检查 URL，并用 `GET /v1/models` 确认可用模型名 |
| `400` / `422` | 参数类型、消息角色或 tool schema 错误 | 阅读响应 `error.message`，用最小请求逐项恢复参数 |
| `429` | 并发或请求速率超过服务限制 | 遵守 `Retry-After`，使用带抖动的指数退避 |
| `500` / `503` | 服务过载、GPU OOM 或后端异常 | 限次重试，持续失败时查看服务端日志与显存 |
| 请求超时 | 首次加载、长输出或排队 | 调小 `max_tokens`、设置合理客户端超时、检查队列 |
| 流式没有输出 | 代理缓存 SSE、客户端未逐块读取 | 禁用代理缓冲，确认传入 `stream=true` 并遍历迭代器 |
| 没有工具调用 | 服务未开启自动工具选择或解析器 | vLLM 启用 `--enable-auto-tool-choice --tool-call-parser hy_v3` |
| 没有推理字段 | 服务未配置 reasoning parser | vLLM 使用 `--reasoning-parser hy_v3`，SGLang 使用 `hunyuan` |

只对超时、网络错误、`429` 和 `5xx` 重试。`400`、`401`、`403`、`404` 通常需要修正请求，自动重试不会解决问题。
