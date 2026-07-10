# Hy3 API 快速开始

[English](quickstart.md)

## 前置条件

你需要：

- 本仓库代码，以及带有 `venv` 和 `pip` 的 Python 环境。
- 一个自部署的 Hy3 OpenAI 兼容接口，或 OpenRouter 账号。
- 如果选择自部署，先使用仓库中的 [vLLM](README_CN.md#vllm) 或 [SGLang](README_CN.md#sglang) 命令启动 Hy3。

创建隔离环境并安装示例依赖：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r examples/api/requirements.txt
cp examples/api/.env.example examples/api/.env
```

在 Windows PowerShell 中，使用 `.\.venv\Scripts\Activate.ps1` 激活环境，并用 `Copy-Item examples/api/.env.example examples/api/.env` 复制配置模板。

## API 配置

示例会读取 `examples/api/.env`，但不会覆盖 shell 中已存在的环境变量。

| 变量 | 自部署默认值 | OpenRouter 值 | 用途 |
|---|---|---|---|
| `HY3_BACKEND` | `self_hosted` | `openrouter` | 选择请求体映射。 |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | `https://openrouter.ai/api/v1` | OpenAI 兼容 API 的基础地址。 |
| `HY3_API_KEY` | `EMPTY` | 保存 OpenRouter key 的环境变量 | 传给 SDK 的认证值。 |
| `HY3_MODEL` | `hy3` | `tencent/hy3:free` | 每次请求使用的模型名。 |
| `HY3_TIMEOUT` | `120` | `120` 或其他有限正数 | SDK 超时时间，单位为秒。 |

自部署 `.env`：

```dotenv
HY3_BACKEND=self_hosted
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
HY3_TIMEOUT=120
```

OpenRouter 配置把 key 保留在环境变量中：

```bash
# 运行前先在 shell 或 secret manager 中设置 HY3_API_KEY。
export HY3_BACKEND=openrouter
export HY3_BASE_URL=https://openrouter.ai/api/v1
export HY3_MODEL=tencent/hy3:free
export HY3_TIMEOUT=120
```

Windows PowerShell 对应配置：

```powershell
# 运行前先通过 secret manager 设置 $env:HY3_API_KEY。
$env:HY3_BACKEND = "openrouter"
$env:HY3_BASE_URL = "https://openrouter.ai/api/v1"
$env:HY3_MODEL = "tencent/hy3:free"
$env:HY3_TIMEOUT = "120"
```

## 五分钟首次调用

配置任一后端后，从仓库根目录运行第一个示例：

```bash
python examples/api/01_basic_chat.py
```

脚本先发送单轮请求，再把第一次响应的 assistant content 加入历史并发送第二轮请求。后端提供时，脚本还会输出规范化后的 reasoning、finish reason 和 usage。完整请求和确定性测试输出见[基础对话指南](examples/api/01_basic_chat_CN.md)。

## curl

自部署的原始 HTTP JSON 在顶层使用 `chat_template_kwargs`：

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer EMPTY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

OpenRouter 的原始 HTTP JSON 在顶层使用 `reasoning`，key 仅从 `${HY3_API_KEY}` 读取：

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tencent/hy3:free",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "reasoning": {"effort": "none"}
  }'
```

以上是线上传输格式。两个 curl 请求体都不包含 SDK 专用包装字段。

## Python SDK

OpenAI Python SDK 通过 `extra_body` 接收提供方专用字段。

自部署：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)
print(response.choices[0].message.content)
```

OpenRouter：

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["HY3_API_KEY"],
)
response = client.chat.completions.create(
    model="tencent/hy3:free",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"reasoning": {"effort": "none"}},
)
print(response.choices[0].message.content)
```

## 原始 JSON 与 SDK 参数差异

`extra_body` 是 OpenAI SDK 参数，不是 HTTP 字段。SDK 会把其中内容合并到最终 JSON 对象的顶层。

| 后端 | curl 原始 JSON | Python SDK 参数 |
|---|---|---|
| 自部署 | 请求体顶层的 `chat_template_kwargs.reasoning_effort` | `extra_body={"chat_template_kwargs": {"reasoning_effort": effort}}` |
| OpenRouter | 请求体顶层的 `reasoning.effort` | `extra_body={"reasoning": {"effort": mapped_effort}}` |

对 OpenRouter，示例把 Hy3 的 `no_think` 映射为 `none`；`low` 和 `high` 名称保持不变。

## 参数

| 参数 | 在这些示例中的含义 |
|---|---|
| `temperature` | 采样温度。示例使用 `0.9`。 |
| `top_p` | 核采样阈值。示例使用 `1.0`。 |
| `max_tokens` | 最大生成 token 数；不同任务使用 `128`、`256` 或 `512`。 |
| `stop` | 可选字符串或字符串列表，匹配时停止生成；六个示例没有设置。 |
| `stream` | 设为 `true` 时返回 chunk，而不是单个 completion。 |
| `stream_options` | 使用 `{"include_usage": true}` 请求后端在支持时于结束阶段返回仅含 usage 的 chunk。 |
| `tools` | 提供给模型的函数 schema。 |
| `tool_choice` | 工具示例使用 `auto`，允许直接回答或返回一个/多个工具调用。 |
| 推理强度 | 自部署使用 `no_think`、`low`、`high`；OpenRouter 在传输格式中使用 `none`、`low`、`high`。 |

## 推理模式

直接回答使用 `no_think`，较轻推理使用 `low`，复杂推理任务使用 `high`。reasoning 字段是可选的：后端只返回 content，而没有 `reasoning`、`reasoning_content` 或 `reasoning_details`，仍是合法响应。

[推理模式对比示例](examples/api/05_reasoning_mode_CN.md)对 `no_think` 和 `high` 使用相同问题、采样参数和 token 上限，仅改变后端映射后的 effort。向最终用户展示推理内容前，请先确认产品策略和提供方行为。

## 流式输出

使用 SDK 时设置 `stream=True` 和 `stream_options={"include_usage": True}`。健壮的消费者必须接受：

- `choices` 为空的 chunk；
- content 与 reasoning 出现在不同 delta；
- 通过 `index` 标识的交错工具调用分片；
- 最后一个只含 usage 的 chunk。

共享的 `StreamAccumulator` 会处理这些情况：实时只打印 content，reasoning 单独保存，并按 index 排序重组工具调用。参阅[流式输出](examples/api/02_streaming_CN.md)和[流式与非流式对比](examples/api/03_streaming_vs_non_streaming_CN.md)。

## 工具调用

工具调用既需要请求 schema，也需要带兼容 parser 的服务端。

仓库的 [vLLM 部署命令](README_CN.md#vllm)包含：

```text
--tool-call-parser hy_v3
--reasoning-parser hy_v3
--enable-auto-tool-choice
```

仓库的 [SGLang 部署命令](README_CN.md#sglang)使用：

```text
--tool-call-parser hunyuan
--reasoning-parser hunyuan
```

[工具调用指南](examples/api/04_tool_calling_CN.md)演示 `tools`、`tool_choice="auto"`、同一 assistant 回合返回多个调用、匹配的 `tool_call_id`、结构化参数错误和有界循环。示例会顺序执行这些调用。北京/深圳天气值是确定性演示数据，不是实时天气。

## 速率限制

不要假设固定的 QPS、RPM 或 TPM：

- 自部署容量取决于 GPU 显存、并发、模型服务配置和前置网关。
- OpenRouter 限制会动态变化，并取决于账号和提供方。

应处理 HTTP 429；存在有限的数值型 `Retry-After` 时遵循该值，否则采用有界退避。[重试指南](examples/api/06_error_handling_retry_CN.md)展示了这一策略，不发布固定限制。

## 故障排查

| 现象 | 检查与处理 |
|---|---|
| Connection refused | 确认自部署进程正在运行、端口为 `8000`，并且 `HY3_BASE_URL` 以 `/v1` 结尾。 |
| HTTP 401 或 403 | 自部署示例使用 `EMPTY`；OpenRouter 要求 `HY3_API_KEY` 环境变量中有有效 key。不要把真实 key 写入文档或版本库。 |
| Model not found | 让 `HY3_MODEL` 与服务名一致：仓库部署命令暴露 `hy3`；OpenRouter 使用 `tencent/hy3:free`。 |
| Invalid fields | 原始 JSON 在顶层发送 `chat_template_kwargs` 或 `reasoning`；`extra_body` 只作为 SDK 调用参数。 |
| Context overflow | 减少历史消息、工具 payload 或 `max_tokens`；模型公开上下文长度并不消除服务端 token 和显存限制。 |
| Empty stream | 接受空 choices chunk，确认 `stream=True`，并检查最终累计结果，不要假设每个 chunk 都有 content。 |
| Missing tool calls | 检查服务 parser 参数、`tools` schema 和 `tool_choice`；模型也可能合法地选择直接回答。 |
| Missing reasoning | reasoning 字段可缺失。检查 effort 和后端映射，不要把缺少 reasoning 当成损坏的 completion。 |
| HTTP 429 | 遵循有限的数值型 `Retry-After`；否则使用有界 jitter 重试。OpenRouter 限制是动态的。 |
| 瞬时 5xx 或传输错误 | 仅进行有限次数重试，并在最后一次失败时重新抛出。不要重试 400、401、403、404 等永久性 4xx。 |
| 自部署 CUDA OOM | 降低并发或 token 上限，检查 tensor parallelism 和 GPU 容量，并对照仓库的 vLLM/SGLang 部署章节。 |

## 示例学习路径

继续阅读 [API 示例索引](examples/api/README_CN.md)：

1. [基础对话](examples/api/01_basic_chat_CN.md)
2. [流式输出](examples/api/02_streaming_CN.md)
3. [流式与非流式对比](examples/api/03_streaming_vs_non_streaming_CN.md)
4. [工具调用](examples/api/04_tool_calling_CN.md)
5. [推理模式](examples/api/05_reasoning_mode_CN.md)
6. [错误处理与重试](examples/api/06_error_handling_retry_CN.md)

每份指南都链接到可运行的 `.py` 文件和另一语言版本。
