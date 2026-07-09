# Hy3 API 快速开始

本指南帮助你在 5 分钟内完成第一次 Hy3 API 调用，并在 30 分钟内了解模型的主要能力。

Hy3 提供 **OpenAI 兼容** 的 API，你可以直接复用现有的 OpenAI 客户端代码与生态。在开始之前，请先按 [README](./README.md) 中的部署章节，通过 vLLM 或 SGLang 在本地启动服务。

---

## 目录

- [1. 基础信息](#1-基础信息)
- [2. 最小可运行示例](#2-最小可运行示例)
- [3. 参数说明](#3-参数说明)
- [4. 常见报错排查](#4-常见报错排查)

---

## 1. 基础信息

| 项目 | 值 | 说明 |
|:---|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` | 本地部署（vLLM / SGLang）默认地址，端口 `8000`，路径前缀 `/v1` |
| API Key | `EMPTY` | 本地部署不校验密钥，任意非空字符串均可，推荐使用 `EMPTY` 占位 |
| 模型名（model） | `hy3` | 对应启动参数 `--served-model-name hy3`，必须完全匹配 |
| API 协议 | OpenAI 兼容 | 可直接使用 `openai` Python SDK、`curl`、以及任何兼容 OpenAI 的客户端 |
| 上下文长度 | 256K | 单次请求的输入 + 输出 token 总和上限 |
| 推理后端 | vLLM / SGLang | 任选其一，均提供 Hy3 专用 recipe |
| 部署硬件 | 8 张 GPU（推荐 H20-3e） | 295B MoE 模型，需要较大显存 |

### 速率限制说明

- **本地部署没有统一的硬性速率限制**：实际并发能力完全由 vLLM / SGLang 的启动配置（如 `--tensor-parallel-size`、KV cache 大小、连续批处理参数、显存容量）决定。
- **并发与上下文长度的权衡**：Hy3 支持 256K 上下文，但单请求上下文越长，KV cache 占用越大，可同时服务的并发请求数越少。长上下文场景下建议适当控制并发，避免显存溢出（OOM）或排队等待过久。
- **吞吐量受硬件影响显著**：在 8 卡 H20-3e 上可获得较好吞吐；显存更小的卡需要降低并发或缩短上下文。
- **生产 / 云端 API 可能不同**：若使用腾讯云或第三方托管的 Hy3 服务，通常会配置 QPS、TPM、并发数等限额，具体以服务方文档为准，本文档的示例与说明仅针对本地自部署场景。

---

## 2. 最小可运行示例

> 前置条件：已按 [README](./README.md) 部署章节在本地启动 vLLM 或 SGLang 服务，并确认 `http://127.0.0.1:8000/v1` 可访问。

### 2.1 curl 示例

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "用一句话介绍一下你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

> 说明：`curl` 直接走 HTTP，`chat_template_kwargs` 放在请求体顶层即可；通过 OpenAI SDK 调用时则需放入 `extra_body`（见下文）。

预期返回（结构示例，实际内容由模型生成）：

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "我是 Hy3，由腾讯混元团队开发的……"},
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 12, "completion_tokens": 28, "total_tokens": 40}
}
```

### 2.2 Python OpenAI SDK 示例

先安装 SDK：

```bash
pip install openai
```

运行以下脚本：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",  # 本地部署任意非空字符串均可
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "用一句话介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    # 思考模式开关，通过 extra_body.chat_template_kwargs 传入
    # "no_think"（默认，直接作答）/ "low"（轻度思维链）/ "high"（深度思维链）
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

print(response.choices[0].message.content)
```

成功运行后，终端会打印模型的回复。至此你已完成第一次 Hy3 API 调用。

---

## 3. 参数说明

以下参数均可通过 OpenAI 兼容接口传递。Python SDK 中直接作为关键字参数，`curl` 中放在 JSON 请求体内。

### 3.1 temperature

| 项 | 内容 |
|:---|:---|
| 含义 | 控制采样随机性。值越高，输出越发散、富有创造性；值越低，输出越确定、聚焦。 |
| 取值范围 | `0.0` ~ `2.0`（建议 `0.0` 以上） |
| 推荐值 | **`0.9`**（Hy3 官方推荐） |
| 备注 | 严格确定性输出场景可设为 `0`；但过低的 temperature 偶尔会放大重复，建议在生产中根据任务微调。 |

### 3.2 top_p

| 项 | 内容 |
|:---|:---|
| 含义 | 核采样（nucleus sampling）阈值，仅从累计概率达到 `top_p` 的候选 token 中采样。 |
| 取值范围 | `0.0` ~ `1.0` |
| 推荐值 | **`1.0`**（Hy3 官方推荐，即不额外截断） |
| 备注 | 一般 `temperature` 与 `top_p` 二选一调整，避免同时大幅偏离推荐值。 |

### 3.3 max_tokens

| 项 | 内容 |
|:---|:---|
| 含义 | 限制模型单次生成的最大 token 数（不含输入）。 |
| 取值范围 | `1` ~ `上下文长度 - 输入 token 数`（Hy3 上下文长度为 256K） |
| 推荐值 | 按任务设置：闲聊 512~2048；长文档/代码生成 4096~8192；复杂推理（`high` 思考模式）建议 ≥ 8192 以容纳思维链。 |
| 备注 | 不设置时由服务端默认值决定；设置过小可能导致输出被截断（`finish_reason="length"`）。 |

### 3.4 stop

| 项 | 内容 |
|:---|:---|
| 含义 | 停止序列，当生成内容命中其中任一字符串时立即停止输出。 |
| 取值范围 | 字符串或字符串数组（最多若干个，受服务端限制） |
| 推荐值 | 按需设置，例如 `["\nUser:", "<|im_end|>"]` 用于多轮对话截断。 |
| 备注 | 停止序列本身不会出现在返回内容中；`finish_reason` 会置为 `"stop"`。 |

### 3.5 tools（工具调用）

| 项 | 内容 |
|:---|:---|
| 含义 | 向模型声明可调用的外部工具（函数），模型可在回复中产出结构化工具调用，由客户端执行后回传结果。 |
| 取值范围 | JSON Schema 描述的工具数组，格式遵循 OpenAI `tools` 规范 |
| 推荐值 | 依据业务定义；Hy3 在智能体 / 工具调用场景有专门优化。 |
| 备注 | **必须配合正确的 tool-call 解析器启动服务**：<br>• vLLM：`--tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice`<br>• SGLang：`--tool-call-parser hunyuan --reasoning-parser hunyuan` |

工具调用示例：

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称，例如：北京"}
                },
                "required": ["city"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "北京今天天气怎么样？"}],
    tools=tools,
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

tool_calls = response.choices[0].message.tool_calls
if tool_calls:
    print("模型请求调用工具：", tool_calls[0].function.name, tool_calls[0].function.arguments)
else:
    print(response.choices[0].message.content)
```

### 3.6 思考模式开关 reasoning_effort

Hy3 支持通过 `reasoning_effort` 切换思考深度，**必须经由 `extra_body.chat_template_kwargs` 传入**（OpenAI SDK），或在原始 HTTP 请求体的 `chat_template_kwargs` 字段中传入。

| 取值 | 行为 | 适用场景 |
|:---|:---|:---|
| `"no_think"` | 直接作答，不生成思维链（默认） | 闲聊、简单问答、对延迟敏感的在线场景 |
| `"low"` | 轻度思维链 | 需要少量推理、结构化输出、多约束遵循 |
| `"high"` | 深度思维链，充分推理 | 数学、编程、复杂逻辑推理等难题 |

用法示例：

```python
# 深度思考模式：适合数学 / 代码 / 复杂推理
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "证明：任意偶数大于 2 都可以表示为两个素数之和（哥德巴赫猜想）的数值验证，请给出 100 以内的验证。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=8192,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
print(response.choices[0].message.content)
```

> 提示：开启 `high` 时思维链会消耗较多 token，请适当调大 `max_tokens`，并留意单请求耗时上升。

---

## 4. 常见报错排查

### 4.1 连接失败

**现象**：`curl: (7) Failed to connect to 127.0.0.1 port 8000` / Python 报 `ConnectionError`、`Connection refused`。

**可能原因**：
- vLLM / SGLang 服务未启动，或启动过程中加载模型失败已退出。
- 端口被占用或与启动参数 `--port` 不一致。
- 服务监听在 `0.0.0.0` 但客户端访问的地址不对，或防火墙拦截。

**排查与解决**：
1. 确认进程存活：检查 vLLM / SGLang 启动日志是否打印出 "Application startup complete" / "Uvicorn running on"。
2. 确认端口：`curl http://127.0.0.1:8000/v1/models` 能返回模型列表。
3. 若日志有 OOM、CUDA error 等，说明模型未成功加载，请按 [README](./README.md) 检查 GPU 数量与显存。
4. 检查启动参数中的 `--port` 是否为 `8000`，以及 `--served-model-name` 是否为 `hy3`。

### 4.2 鉴权失败

**现象**：HTTP `401 Unauthorized`，返回 `{"error": "...invalid api key..."}` 之类信息。

**可能原因**：
- 客户端传入的 `api_key` 为空字符串或 `None`，部分客户端会因此拒绝发送请求。
- 误将本地部署当作云端鉴权服务，使用了错误的密钥格式。
- 服务端被反向代理加上了额外的鉴权层。

**排查与解决**：
- 本地部署时 `api_key` 传任意非空字符串即可，推荐统一用 `"EMPTY"`。
- 确认 SDK 实例化时显式传入：`OpenAI(base_url=..., api_key="EMPTY")`。
- 若经过网关 / 代理，请向网关维护方索取正确的鉴权方式。

### 4.3 模型未找到

**现象**：HTTP `404` 或 `400`，返回 `model "xxx" not found` / `The model `xxx` does not exist`。

**可能原因**：
- 请求中的 `model` 字段与服务端 `--served-model-name` 不匹配（注意大小写）。
- 服务端模型加载失败或正在加载中，尚未注册到 `/v1/models`。

**排查与解决**：
1. 调用 `curl http://127.0.0.1:8000/v1/models` 查看实际可用的模型名。
2. 确保请求中 `model="hy3"`，与服务端 `--served-model-name hy3` 完全一致。
3. 若模型仍在加载，等待日志出现服务就绪信息后再调用。

### 4.4 超时

**现象**：客户端抛出 `ReadTimeout` / `APITimeoutError`，或长时间无响应后断开。

**可能原因**：
- 请求输入过长（接近 256K 上限）或 `max_tokens` 过大，单次生成耗时超过客户端默认超时。
- 开启 `high` 思考模式导致 token 生成量大幅增加。
- 服务端并发过高、排队严重，或显存压力下批处理变慢。

**排查与解决**：
1. 适当调大客户端超时：Python SDK 中 `client = OpenAI(base_url=..., api_key="...", timeout=600.0)`，或单请求 `client.chat.completions.create(..., timeout=600.0)`。
2. 评估输入长度，必要时分段处理，避免一次性贴近 256K 上限。
3. `high` 思考模式下适当调大 `max_tokens`，但同时关注耗时；对延迟敏感的任务可降级为 `low` 或 `no_think`。
4. 监控服务端 GPU 利用率与显存，必要时降低并发或扩容。

### 4.5 限流

**现象**：HTTP `429 Too Many Requests`，返回 `rate limit exceeded` 之类信息。

**可能原因**：
- 本地部署虽无统一硬限制，但当并发请求超过 vLLM / SGLang 调度能力（受显存、KV cache、批处理上限约束）时，服务端可能主动拒绝或排队超时。
- 经由网关 / 云端服务时，触发了上游配置的 QPS / 并发限额。

**排查与解决**：
1. 降低客户端并发，加入重试与指数退避（如 `tenacity`、`backoff` 库）。
2. 在服务端调优：增大 KV cache、开启连续批处理、合理设置 `--max-num-seqs` 等参数（参见 vLLM / SGLang 文档）。
3. 长上下文场景优先控制并发数，必要时用排队机制削峰。
4. 云端服务请参考其官方限额说明，申请提升配额或按配额规划调用节奏。

---

## 下一步

- 了解完整部署流程：见 [README](./README.md) 的 Deployment 章节。
- 进行微调：见 [微调指南](./finetune/README.md)。
- 反馈与交流：邮箱 `hunyuan_opensource@tencent.com`。
