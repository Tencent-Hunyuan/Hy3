# Hy3 API Quickstart

本文面向已经启动 Hy3 推理服务的开发者，目标是 5 分钟跑通第一次调用，半小时掌握常用能力。Hy3 服务通过 vLLM 或 SGLang 暴露 OpenAI-compatible API，调用方式与 OpenAI Chat Completions 接近。

## 0. 启动服务

先按照根目录 `README.md` / `README_CN.md` 的部署章节启动 vLLM 或 SGLang，并确认启动参数里包含：

```bash
--served-model-name hy3
--tool-call-parser hy_v3      # vLLM
--reasoning-parser hy_v3      # vLLM
```

SGLang 对应参数为：

```bash
--served-model-name hy3
--tool-call-parser hunyuan
--reasoning-parser hunyuan
```

如果你只想验证 API 客户端代码，可以先把下面的环境变量指向任意兼容 OpenAI Chat Completions 的 Hy3 服务。

## 1. 基础信息

| 项目 | 默认值 | 说明 |
| --- | --- | --- |
| Base URL | `http://127.0.0.1:8000/v1` | vLLM/SGLang 本地服务默认示例地址。SGLang 如果使用默认端口 30000，请改成 `http://127.0.0.1:30000/v1`。 |
| API key | `EMPTY` | 本地服务未配置鉴权时可用任意非空字符串。若启动服务时设置了 `--api-key` 或前面接了网关，请使用真实 key。 |
| Model name | `hy3` | 与服务启动时的 `--served-model-name hy3` 保持一致。 |
| Endpoint | `/chat/completions` | 完整 URL 为 `${HY3_BASE_URL}/chat/completions`。 |
| Rate limits | 无固定模型侧限制 | 自部署场景的有效限流由 GPU 显存、并发、队列、`max_model_len`、vLLM/SGLang 调度和网关策略共同决定。生产环境建议在 API 网关层设置 QPS、并发和超时限制。 |

## 2. Provider 配置

所有 examples 都通过 `examples/api/common.py` 读取环境变量。默认配置面向本地 vLLM/SGLang；设置 `HY3_PROVIDER` 后可切换到 OpenRouter、腾讯云混元或其他 OpenAI-compatible 网关。

推荐把配置写在仓库根目录 `.env`，也就是和 `quickstart.md` 同级的位置：

```bash
cp .env.example .env
```

然后编辑 `.env`，选择本地、OpenRouter、腾讯云或自定义网关其中一种配置。`examples/api/*.py` 会自动加载根目录 `.env`；如果同名变量已经在 shell 中通过 `export` 设置，shell 变量优先。

### 本地 vLLM / SGLang

```bash
export HY3_PROVIDER="local"
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
```

本地模式默认会发送 Hy3 chat template 参数：

```json
{"chat_template_kwargs": {"reasoning_effort": "no_think"}}
```

### OpenRouter

OpenRouter 官方 OpenAI SDK base URL 为 `https://openrouter.ai/api/v1`，鉴权使用 Bearer API key。OpenRouter 还支持可选的应用归因 headers：`HTTP-Referer` 和 `X-OpenRouter-Title`。

```bash
export HY3_PROVIDER="openrouter"
export HY3_BASE_URL="https://openrouter.ai/api/v1"
export OPENROUTER_API_KEY="<your-openrouter-api-key>"
export HY3_MODEL="<openrouter-model-slug>"

# Optional attribution headers.
export OPENROUTER_HTTP_REFERER="https://your-site.example"
export OPENROUTER_APP_TITLE="Your App Name"
```

说明：

- `HY3_MODEL` 必须是 OpenRouter 当前可用的 model slug；如果 OpenRouter 上架 Hy3，请填对应 slug。
- 不应假定 OpenRouter 上的目标模型支持 Hy3 本地模板扩展参数，因此 examples 在 `HY3_PROVIDER=openrouter` 时默认不发送 `chat_template_kwargs`，而是使用 OpenRouter 标准 `reasoning` 参数。
- OpenRouter 下 examples 会自动映射 `reasoning_effort="no_think"` 为 `{"reasoning": {"effort": "none"}}`，避免 `tencent/hy3:free` 把全部 `max_tokens` 用在 reasoning tokens 上而返回空 `content`。
- 如你的 OpenRouter 路由后端确实支持 Hy3 模板扩展，可显式设置 `HY3_SEND_REASONING=true`。

### 腾讯云混元 OpenAI 兼容接口

腾讯云混元官方 OpenAI 兼容 base URL 为 `https://api.hunyuan.cloud.tencent.com/v1`，完整 chat completions 地址为 `https://api.hunyuan.cloud.tencent.com/v1/chat/completions`。API key 需要在腾讯云控制台创建。腾讯云文档示例模型为 `hunyuan-turbos-latest`；如果你的账号或服务暴露了 Hy3 相关模型名，请把 `HY3_MODEL` 改为实际模型名。

```bash
export HY3_PROVIDER="tencent"
export HY3_BASE_URL="https://api.hunyuan.cloud.tencent.com/v1"
export HUNYUAN_API_KEY="<your-hunyuan-api-key>"
export HY3_MODEL="hunyuan-turbos-latest"

# Optional Tencent custom body. For example:
export HY3_EXTRA_BODY_JSON='{"enable_enhancement": true}'
```

说明：

- 腾讯云混元文档中的生文接口默认并发限制为 5 个并发，实际限额以账号、模型和控制台配置为准。
- 不应假定腾讯云混元接口支持 Hy3 本地模板扩展参数，因此 examples 在 `HY3_PROVIDER=tencent` 时默认不发送 `chat_template_kwargs`。

### 其他 OpenAI-compatible 网关

```bash
export HY3_PROVIDER="custom"
export HY3_BASE_URL="https://your-gateway.example/v1"
export HY3_API_KEY="<your-api-key>"
export HY3_MODEL="<served-model-name>"
```

如果该远程网关是你自建的 Hy3 vLLM/SGLang 服务，并支持 Hy3 reasoning parser，可打开：

```bash
export HY3_SEND_REASONING=true
```

## 3. 最小可运行示例

### curl

本地 vLLM/SGLang 请求可以直接携带 Hy3 模板参数：

```bash
curl "${HY3_BASE_URL:-http://127.0.0.1:8000/v1}/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY:-EMPTY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"${HY3_MODEL:-hy3}"'",
    "messages": [
      {"role": "user", "content": "Hello! Introduce Hy3 in one sentence."}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 128,
    "chat_template_kwargs": {
      "reasoning_effort": "no_think"
    }
  }'
```

OpenRouter / 腾讯云这类云服务通常使用普通 OpenAI-compatible body，不要默认携带本地 Hy3 `chat_template_kwargs`：

```bash
curl "${HY3_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY:-${OPENROUTER_API_KEY:-${HUNYUAN_API_KEY}}}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "'"${HY3_MODEL}"'",
    "messages": [
      {"role": "user", "content": "Hello! Introduce yourself in one sentence."}
    ],
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 128
  }'
```

返回中最常用字段：

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1783400000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hy3 is Tencent's MoE language model for agentic, reasoning, and long-context tasks."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 32,
    "completion_tokens": 22,
    "total_tokens": 54
  }
}
```

### Python OpenAI SDK

安装依赖：

```bash
python3 -m pip install "openai>=1.0.0"
```

运行：

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.getenv("HY3_API_KEY", os.getenv("OPENROUTER_API_KEY", os.getenv("HUNYUAN_API_KEY", "EMPTY"))),
)

response = client.chat.completions.create(
    model=os.getenv("HY3_MODEL", "hy3"),
    messages=[
        {"role": "user", "content": "Hello! Introduce Hy3 in one sentence."},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

message = response.choices[0].message
print("finish_reason:", response.choices[0].finish_reason)
print("content:", message.content)
print("usage:", response.usage)
```

远程云服务不一定支持 `extra_body={"chat_template_kwargs": ...}`。本仓库 examples 已经通过 `HY3_PROVIDER` 做了默认区分：本地发送，OpenRouter / 腾讯云不发送。

## 4. 常用参数

| 参数 | 类型 | 建议起点 | 说明 |
| --- | --- | --- | --- |
| `temperature` | number | `0.9` | 控制随机性。越低越稳定，越高越发散。代码生成、结构化输出可从 `0.2` 到 `0.7` 试起；开放创作可使用 `0.9`。 |
| `top_p` | number | `1.0` | nucleus sampling 截断概率。通常与 `temperature` 二选一优先调节；不确定时保持 `1.0`。 |
| `max_tokens` | integer | `128` 到 `2048` | 限制本次生成的最大 token 数。过小会导致 `finish_reason="length"`；过大增加延迟和显存压力。 |
| `stop` | string 或 array | 视任务而定 | 命中 stop 序列后停止生成。适合模板化输出、分隔符协议、日志切分。 |
| `tools` | array | 仅工具调用任务开启 | OpenAI-compatible tool calling。需要服务启动时启用对应 tool call parser，并在客户端实现本地工具执行循环。 |
| `extra_body.chat_template_kwargs.reasoning_effort` | string | `"no_think"` | Hy3 思考模式开关。`"no_think"` 为直接回答；`"low"` 适合中等推理；`"high"` 适合数学、代码、复杂规划等任务。 |
| `HY3_EXTRA_BODY_JSON` | JSON object | unset | 给云服务或自建网关传 provider-specific 顶层参数，例如腾讯云 `{"enable_enhancement": true}`。 |

Reasoning 内容是否在响应里以 `message.reasoning_content` 暴露，取决于服务端 reasoning parser 和推理框架支持。即使未暴露 reasoning 字段，`reasoning_effort` 仍会传给 chat template。

## 5. Examples

示例目录：`examples/api/`

| 能力 | 文件 | 说明 |
| --- | --- | --- |
| Basic chat | `examples/api/basic_chat.py` / `.md` | 单轮与多轮对话。 |
| Streaming | `examples/api/streaming.py` / `.md` | 流式请求与逐 chunk 解析。 |
| Non-streaming vs streaming | `examples/api/latency_compare.py` / `.md` | 首 token 时延和总耗时对比。 |
| Tool calling | `examples/api/tool_calling.py` / `.md` | 一次工具调用与多轮工具循环。 |
| Reasoning mode | `examples/api/reasoning_mode.py` / `.md` | 思考模式开/关对比。 |
| Error handling & retry | `examples/api/retry.py` / `.md` | 超时、限流、网络错误的重试与退避。 |

运行前确认：

```bash
python3 -m pip install "openai>=1.0.0"
cp .env.example .env

# Edit .env, or export variables directly:
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
```

## 6. 常见报错排查

| 现象 | 常见原因 | 处理方式 |
| --- | --- | --- |
| `Connection refused` / `ConnectError` | 服务未启动、端口不对、容器端口未映射 | 检查 vLLM/SGLang 日志；确认 `HY3_BASE_URL` 端口和 `/v1` 后缀。 |
| `401 Unauthorized` / `403 Forbidden` | API key 不匹配，或网关鉴权失败 | 本地无鉴权时用 `EMPTY`；启用 `--api-key` 或网关后使用真实 key。 |
| `404 model not found` | `model` 与 `--served-model-name` 不一致 | 启动服务时使用 `--served-model-name hy3`，或把 `HY3_MODEL` 改成服务实际模型名。 |
| 请求长时间无响应 | 首次加载/预热、队列拥塞、prompt 太长、`max_tokens` 过大 | 先用短 prompt 和小 `max_tokens` 验证；观察服务端 GPU 显存和队列。 |
| `429` / `503` | 网关限流或推理服务过载 | 降低并发，增加指数退避重试，或扩容服务实例。 |
| `finish_reason="length"` | `max_tokens` 太小 | 增大 `max_tokens` 或缩短 prompt。 |
| tool call 解析失败 | 服务未启用 tool call parser，或工具 JSON schema 太复杂 | 确认启动参数；先用简单 schema 验证；在客户端记录原始 `tool_calls`。 |
| 没有 `reasoning_content` | 服务端未启用 reasoning parser，或框架没有分离返回思考内容 | 确认 `--reasoning-parser`；客户端用 `getattr(message, "reasoning_content", None)` 做兼容。 |
| context length / token limit 错误 | 输入超过服务配置或模型上下文限制 | 缩短历史消息、启用摘要、降低单次输入长度，或调整服务端最大上下文配置。 |
| OpenRouter `401` | `OPENROUTER_API_KEY` 未设置或 key 无效 | 设置 `HY3_PROVIDER=openrouter` 和 `OPENROUTER_API_KEY`；确认账户额度和模型可用性。 |
| OpenRouter `404` / model not found | `HY3_MODEL` 不是 OpenRouter model slug | 到 OpenRouter models 页面确认当前 slug。 |
| 腾讯云 `401` / `403` | `HUNYUAN_API_KEY` 未设置、权限或计费状态异常 | 设置 `HY3_PROVIDER=tencent` 和 `HUNYUAN_API_KEY`；检查控制台 API key、服务开通和额度。 |
| 云服务报不认识 `chat_template_kwargs` | 把本地 Hy3 模板参数发送到了云 API | 使用 `HY3_PROVIDER=openrouter` 或 `HY3_PROVIDER=tencent`，或设置 `HY3_SEND_REASONING=false`。 |

## 7. 参考文档

- OpenRouter Quickstart: https://openrouter.ai/docs/quickstart
- OpenRouter API Reference: https://openrouter.ai/docs/api/reference/overview
- 腾讯云混元 OpenAI 兼容接口示例: https://cloud.tencent.com/document/product/1729/111007

## 8. 下一步

从 `examples/api/basic_chat.py` 开始跑通基础请求，再根据业务需要依次验证 streaming、tool calling、reasoning mode 和 retry 策略。
