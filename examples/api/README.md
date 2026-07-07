# Hy3 API Examples

这些示例覆盖 Hy3 OpenAI-compatible API 的常用开发场景。每个 `.py` 文件都可以独立运行；同名 `.md` 文件包含完整请求、响应解析说明和示例输出。

## 环境变量

```bash
python3 -m pip install "openai>=1.0.0"
cp .env.example .env
```

`.env` 文件放在仓库根目录，也就是和 `quickstart.md` 同级。所有 `examples/api/*.py` 脚本都会自动加载这个文件；如果同名变量已经在 shell 中设置，shell 变量优先。

### 本地 vLLM / SGLang

```bash
export HY3_PROVIDER="local"
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
```

如果使用 SGLang 默认端口，通常改为：

```bash
export HY3_BASE_URL="http://127.0.0.1:30000/v1"
```

### OpenRouter

```bash
export HY3_PROVIDER="openrouter"
export HY3_BASE_URL="https://openrouter.ai/api/v1"
export OPENROUTER_API_KEY="<your-openrouter-api-key>"
export HY3_MODEL="<openrouter-model-slug>"

# Optional attribution headers used by OpenRouter.
export OPENROUTER_HTTP_REFERER="https://your-site.example"
export OPENROUTER_APP_TITLE="Your App Name"
```

`HY3_MODEL` 必须使用 OpenRouter 当前可用的 model slug。如果 OpenRouter 暂未提供 Hy3，请选择业务实际要调用的模型或接入你自己的 Hy3 网关。

### 腾讯云混元 OpenAI 兼容接口

```bash
export HY3_PROVIDER="tencent"
export HY3_BASE_URL="https://api.hunyuan.cloud.tencent.com/v1"
export HUNYUAN_API_KEY="<your-hunyuan-api-key>"
export HY3_MODEL="hunyuan-turbos-latest"

# Optional Tencent custom body.
export HY3_EXTRA_BODY_JSON='{"enable_enhancement": true}'
```

如腾讯云或你的企业网关暴露了 Hy3 专用模型名，请把 `HY3_MODEL` 改成服务实际返回的模型名。

### Provider-specific body

示例默认行为：

- `HY3_PROVIDER=local` / `vllm` / `sglang`：自动发送 `chat_template_kwargs.reasoning_effort`。
- `HY3_PROVIDER=openrouter`：默认发送 OpenRouter 标准 `reasoning` 参数，例如 `no_think -> {"effort": "none"}`、`high -> {"effort": "high"}`。
- `HY3_PROVIDER=tencent`：默认不发送 Hy3 本地模板参数，避免目标云模型不兼容。
- 远程服务如果也是 Hy3 vLLM/SGLang 且支持该参数，可设置 `HY3_SEND_REASONING=true`。
- 需要额外顶层 body 参数时，设置 `HY3_EXTRA_BODY_JSON`，例如 `{"enable_enhancement": true}`。

## 示例列表

| 场景 | 运行命令 | 文档 |
| --- | --- | --- |
| Basic chat: 单轮 / 多轮 | `python3 examples/api/basic_chat.py` | `examples/api/basic_chat.md` |
| Streaming: 流式请求 + chunk 解析 | `python3 examples/api/streaming.py` | `examples/api/streaming.md` |
| Non-streaming vs streaming: 首 token / 总耗时 | `python3 examples/api/latency_compare.py` | `examples/api/latency_compare.md` |
| Tool calling: 一次调用 + 工具循环 | `python3 examples/api/tool_calling.py` | `examples/api/tool_calling.md` |
| Reasoning mode: 思考开 / 关 | `python3 examples/api/reasoning_mode.py` | `examples/api/reasoning_mode.md` |
| Error handling & retry: 超时 / 限流 / 网络错误 | `python3 examples/api/retry.py` | `examples/api/retry.md` |

## 约定

- 默认 `model` 为 `hy3`，必须与服务启动时的 `--served-model-name` 一致。
- 默认 `api_key` 为 `EMPTY`，适用于未启用鉴权的本地 vLLM/SGLang 服务。
- 远程 provider 的 key 推荐使用 provider 原生命名：OpenRouter 使用 `OPENROUTER_API_KEY`，腾讯云混元使用 `HUNYUAN_API_KEY`。
- 每个脚本都会打印 request body 和关键 response 字段，便于复制到日志或 issue 中排查。
- 示例输出是参考形态，真实文本、token 数、延迟和 tool call 参数会受模型版本、硬件、服务框架和采样参数影响。
