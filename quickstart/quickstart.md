# Hy3 OpenAI 兼容 API 快速开始

本文面向按照仓库说明，使用 vLLM 或 SGLang 自行部署的 Hy3 服务。下面的地址、Key 和模型名均来自仓库当前示例；如果调用的是其他团队或平台托管的服务，请向服务提供方获取实际配置。

## 1. 基础信息

| 配置项 | 信息 | 说明 |
|---|---|---|
| Base URL | `http://127.0.0.1:8000/v1` | API 的根地址。SDK 会在其后请求 `chat/completions`。`127.0.0.1` 只代表运行客户端的本机；跨机器或容器调用时要换成服务实际可访问的地址。 |
| API Key | `EMPTY` | 自部署示例使用该占位值，不可提供真实 Key 的申请入口。 |
| Model | `hy3` | 这是启动命令通过 `--served-model-name hy3` 设置的服务模型名，不是模型下载路径 `tencent/Hy3`。如果部署时改了别名，请以服务端配置为准。 |
| 请求接口 | `POST /chat/completions` | 完整示例地址为 `http://127.0.0.1:8000/v1/chat/completions`。这是 OpenAI 兼容的 Chat Completions 接口。 |
| 模型上下文长度 | `256K` | 服务实际可用长度还可能受推理框架启动配置、显存和输入长度限制。 |
| RPM / 最大并发 | `20次每秒/5路` | 默认接口频率限制一般为20次/秒，默认单账号并发数限制为5路。 |



## 2. 最小可运行示例

以下示例假定 Hy3 已按仓库 README 启动在本机 `8000` 端口，服务模型名为 `hy3`。

### curl

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好！请用一句话介绍自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 128,
    "chat_template_kwargs": {
      "reasoning_effort": "no_think"
    }
  }'
```

Windows PowerShell 中如果 `curl` 被解析为其他命令，可将第一行的 `curl` 改为 `curl.exe`。

### Python OpenAI SDK

安装 SDK：

```bash
python -m pip install -U openai
```

运行示例：

```python
import os

from openai import OpenAI


client = OpenAI(
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好！请用一句话介绍自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    # extra_body 中的字段会被 SDK 放入 HTTP 请求体顶层。
    extra_body={
        "chat_template_kwargs": {
            "reasoning_effort": "no_think",
        }
    },
)

print(response.choices[0].message.content)
```

生产环境建议通过环境变量传入地址和 Key，例如 `HY3_BASE_URL`、`HY3_API_KEY`，不要把真实 Key 硬编码进程序。

## 3. 参数说明

| 参数 | 作用 | Hy3 使用建议与注意事项 |
|---|---|---|
| `temperature` | 控制采样随机性。值越低，回答通常越确定；值越高，输出通常越多样。 | 仓库推荐 `0.9`。仓库没有说明当前 vLLM/SGLang 版本接受的完整取值范围；如果服务返回参数校验错误，以所部署框架版本的 API 定义为准。 |
| `top_p` | 核采样阈值，只从累计概率达到该阈值的候选 Token 中采样。 | 仓库推荐 `1.0`。通常不要同时大幅调整 `temperature` 和 `top_p`，否则较难判断是哪一个参数改变了结果。 |
| `max_tokens` | 限制本次最多生成多少 Token，不是字符数，也不是整个上下文长度。 | 示例使用 `128` 只是为了得到短回答，不代表服务上限。输入 Token 加可生成 Token 不能超过服务实际上下文限制；仓库未公布固定最大输出值。若 `finish_reason` 为 `length`，通常表示输出触及了长度限制。 |
| `stop` | 一个字符串或字符串列表。生成内容遇到其中任一停止序列时提前结束。 | 仅在业务确实有明确终止标记时设置；停止序列通常不会出现在最终正文中。仓库没有说明停止序列数量等后端限制，应以实际部署框架版本为准。 |
| `tools` | 向模型声明可调用的函数及其 JSON 参数结构。模型只返回工具调用意图和参数，真正执行函数、校验参数、处理权限以及把结果回传给模型，都由调用方程序负责。 | vLLM 启动时需要仓库示例中的 `--tool-call-parser hy_v3 --enable-auto-tool-choice`；SGLang 需要 `--tool-call-parser hunyuan`。没有这些解析器时，模型可能输出普通文本而不是结构化 `tool_calls`。 |
| 思考模式 | 通过 `reasoning_effort` 选择直接回答或更深入的推理。 | 原始 HTTP 请求使用顶层 `chat_template_kwargs.reasoning_effort`；Python SDK 使用 `extra_body={"chat_template_kwargs": ...}`。复杂数学、编程和推理任务可用 `high`；直接回答用 `no_think`。 |


## 4. 常见报错排查

不同 vLLM/SGLang 版本及前置网关返回的错误正文可能不同。下面按常见现象排查，不把某个状态码视为 Hy3 固定实现。

| 现象 | 常见原因 | 排查方法 |
|---|---|---|
| `Connection refused`、连接超时 | 服务尚未启动、端口不对、容器端口未映射，或服务只监听本机地址。 | 查看服务启动日志；确认客户端使用的主机名和端口；跨机器/容器访问时确认监听地址、端口映射和防火墙。 |
| `401` / `403` | 服务或网关启用了鉴权，Key 缺失、错误或没有权限。 | 确认请求头格式为 `Authorization: Bearer <API_KEY>`；`EMPTY` 只适用于仓库的无真实凭证示例，托管服务必须使用部署方提供的 Key。 |
| `404 Not Found` | Base URL 缺少 `/v1`、重复写了 `/v1`，或请求路径不是 `/chat/completions`。 | SDK 的 `base_url` 使用 `http://主机:端口/v1`；curl 使用完整的 `/v1/chat/completions`。检查网关是否另加了路径前缀。 |
| `400` / `422`，提示 model 不存在 | 请求中的 `model` 与服务端别名不一致。 | 默认启动命令使用 `--served-model-name hy3`，所以示例传 `hy3`；若部署命令已修改，以实际别名为准，并尝试通过 `GET /v1/models` 核对。 |
| `400` / `422`，提示请求或参数无效 | JSON 格式错误、`messages` 结构不正确、参数类型错误、后端版本不接受某个兼容字段。 | 先只保留 `model` 和 `messages`，确认最小请求成功后逐个加回参数；查看响应正文和服务端日志，不要只看状态码。 |
| 上下文过长、输入长度超限 | 输入 Token 与期望输出 Token 的总量超过服务实际限制。 | 缩短历史消息或输入，减小 `max_tokens`；核对推理框架的上下文启动参数和显存配置。README 的 256K 是模型信息，不保证每个部署都按 256K 提供。 |
| `429 Too Many Requests` | API 网关触发 RPM/TPM/并发限制，或部署层拒绝过载请求。 | 查看响应正文及 `Retry-After` 等响应头（如果有）；降低并发并使用带抖动的指数退避重试；向部署管理员确认实际配额。仓库没有提供固定限额。 |
| `5xx`、CUDA OOM、进程退出 | 显存不足、并发或上下文配置过高、模型加载失败，或推理框架内部错误。 | 首先查看服务端日志；降低并发、上下文长度或批处理压力，并核对张量并行和 GPU 配置。仓库建议 8 卡部署时使用 H20-3e 或其他更大显存卡型。 |
| 思考模式没有生效或思考文本混入正文 | `chat_template_kwargs` 放置层级错误、请求没有显式设置模式，或服务端未启用对应 reasoning parser。 | curl 把 `chat_template_kwargs` 放在 JSON 顶层；Python SDK 通过 `extra_body` 传入；核对 vLLM/SGLang 启动参数中的 reasoning parser，并查看原始 JSON。 |
| `tools` 被忽略、返回普通文本或工具名解析失败 | 服务端没有启用 tool-call parser/自动工具选择，工具 JSON Schema 不完整，或工具名与执行端不一致。 | 核对仓库给出的 tool parser 启动参数；检查 `type/function/name/parameters`；打印原始响应，并让执行端只调用白名单中的工具。 |
| Python SDK 提示未设置 API Key | `OpenAI` 客户端要求提供 `api_key`，即使本地服务不校验。 | 按仓库示例传 `api_key="EMPTY"`，或设置 `HY3_API_KEY` 后由示例代码读取。 |

### 两个快速诊断请求

先检查服务是否可达并尝试查看模型列表：

```bash
curl -i http://127.0.0.1:8000/v1/models \
  -H "Authorization: Bearer EMPTY"
```

再发送只包含必填字段的最小请求：

```bash
curl -i http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

如果最小请求成功、增加某个参数后失败，问题通常在该参数、当前推理框架版本的兼容性或服务端启动配置。保留响应正文和同一时间的服务端日志，通常比只记录 HTTP 状态码更有助于定位问题。
