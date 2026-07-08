<p align="left">
    <a href="./quickstart.md">English</a>&nbsp;｜&nbsp;中文
</p>
<br>

# Hy3 API 快速开始

本指南帮助开发者在约 5 分钟内完成第一次 Hy3 API 调用，并在约 30 分钟内了解主要 API 使用模式。

> 本文假设你已经通过 vLLM 或 SGLang 启动了兼容 OpenAI 的 Hy3 API 服务。如果你是自托管部署，请先启动服务，再运行下面的示例。

## 1. 基础信息

| 项目 | 默认值 | 说明 |
| --- | --- | --- |
| Base URL | `http://127.0.0.1:8000/v1` | 兼容 OpenAI 的 API 根地址。如果服务监听在其他主机或端口，请相应修改。 |
| Chat endpoint | `/chat/completions` | 完整 URL：`${HY3_BASE_URL}/chat/completions`。 |
| API key | `EMPTY` | 本地/自托管服务通常接受占位 key。如果你的网关设置了认证 token，请改用该 token。 |
| Model name | `hy3` | 应与服务端的 `--served-model-name hy3` 保持一致。 |
| 推荐采样参数 | `temperature=0.9`, `top_p=1.0` | 适合通用聊天和编码任务的默认值。 |
| 上下文长度 | 最高 `256K` tokens | 实际可用长度还取决于服务配置和可用内存。 |
| 限流 | 取决于部署 | 本指南中的 Hy3 是自托管服务。限流来自你的服务网关、反向代理、队列或 GPU 容量。将 HTTP `429` 视为限流，并使用指数退避重试。 |

## 2. 安装客户端依赖

```bash
python -m pip install -U openai
```

设置环境变量：

```bash
export HY3_BASE_URL="${HY3_BASE_URL:-http://127.0.0.1:8000/v1}"
export HY3_API_KEY="${HY3_API_KEY:-EMPTY}"
export HY3_MODEL="${HY3_MODEL:-hy3}"
```

可选健康检查：

```bash
curl "${HY3_BASE_URL}/models" \
  -H "Authorization: Bearer ${HY3_API_KEY}"

curl "${HY3_BASE_URL}/health" || true
```

## 3. 最小可运行示例：curl

```bash
curl "${HY3_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好！请简单介绍一下你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "chat_template_kwargs": {
      "reasoning_effort": "no_think"
    }
  }'
```

预期响应结构：

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1760000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是 Hy3..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 16,
    "completion_tokens": 50,
    "total_tokens": 66
  }
}
```

## 4. 最小可运行示例：Python OpenAI SDK

创建 `hello_hy3.py`：

```python
import os
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=60.0)

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "你好！请简单介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

message = response.choices[0].message
print(message.content)
print("用量:", response.usage)
```

运行：

```bash
python hello_hy3.py
```

## 5. 参数参考

| 参数 | 类型 | 示例 | 说明 |
| --- | --- | --- | --- |
| `model` | string | `"hy3"` | 必须与服务端提供的模型名一致。 |
| `messages` | array | `[{"role":"user","content":"..."}]` | 聊天历史。可按需使用 `system`、`user`、`assistant` 和 `tool` 角色。 |
| `temperature` | number | `0.9` | 值越高，随机性越强。确定性任务可使用 `0` 或较小值。 |
| `top_p` | number | `1.0` | 核采样。通常调 `temperature` 或 `top_p` 其中一个，不要同时激进调整。 |
| `max_tokens` | integer | `512` | 生成 token 的最大数量。调低可减少延迟和内存压力。 |
| `stop` | string/array | `["\nObservation:"]` | 出现停止序列时停止生成。 |
| `stream` | boolean | `true` | 如果为 `true`，token 生成后会立即以 chunk 形式返回。适合 UI 展示并降低感知延迟。 |
| `tools` | array | OpenAI function schema | 定义模型可以调用的函数。应用需要执行函数，并把工具结果发回模型。 |
| `tool_choice` | string/object | `"auto"`, `"none"`, `"required"` | 普通工具调用用 `auto`，禁用工具用 `none`，也可以指定函数以强制调用特定工具。 |
| `parallel_tool_calls` | boolean | `false` | 如果你的工具循环期望每条 assistant 消息最多包含一个工具调用，请设为 `false`。 |
| `extra_body.chat_template_kwargs.reasoning_effort` | string | `"no_think"`, `"low"`, `"high"` | Hy3 思考模式开关。快速直接回答用 `"no_think"`，更难的推理、编码或数学任务用 `"high"`。 |

### 思考/推理模式

Python SDK：

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "计算：17 * 23"}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

原始 HTTP JSON 请求体：

```json
{
  "model": "hy3",
  "messages": [{"role": "user", "content": "计算：17 * 23"}],
  "chat_template_kwargs": {"reasoning_effort": "high"}
}
```

如果服务端启动了 reasoning parser，部分框架可能会在响应消息中暴露 `reasoning_content` 字段。面向产品 UI 时，建议默认只展示最终答案；只有在产品策略允许时，才记录或摘要展示推理内容。

### 工具调用

要在 vLLM 中使用自动工具调用，请启动服务时启用兼容 Hy3 的工具解析器并开启自动工具选择。对于 SGLang，请使用它的 Hy/Hunyuan 工具解析器。然后在请求中传入 OpenAI 风格的 `tools` 和 `tool_choice="auto"`。

应用侧需要负责：

1. 定义工具 schema，
2. 带上 `tools` 发送用户请求，
3. 读取 `message.tool_calls`，
4. 在本地执行工具，
5. 追加包含工具结果的 `tool` 消息，
6. 再次调用模型生成最终答案。

参见[工具调用说明](examples/zh-cn/04_tool_calling.md)和 [`examples/zh-cn/04_tool_calling.py`](examples/zh-cn/04_tool_calling.py)。

## 6. 示例索引

完整列表请参考[示例索引](examples/zh-cn/README.md)。

| 说明文档 | 示例脚本 | 演示内容 |
| --- | --- | --- |
| [基础聊天](examples/zh-cn/01_basic_chat.md) | [`01_basic_chat.py`](examples/zh-cn/01_basic_chat.py) | 单轮和多轮聊天。 |
| [流式输出](examples/zh-cn/02_streaming.md) | [`02_streaming.py`](examples/zh-cn/02_streaming.py) | 流式请求和逐 chunk 解析。 |
| [延迟对比](examples/zh-cn/03_latency_compare.md) | [`03_latency_compare.py`](examples/zh-cn/03_latency_compare.py) | 非流式与流式：首 token 延迟和总延迟。 |
| [工具调用](examples/zh-cn/04_tool_calling.md) | [`04_tool_calling.py`](examples/zh-cn/04_tool_calling.py) | 单次工具调用和多轮工具执行循环。 |
| [推理模式](examples/zh-cn/05_reasoning_mode.md) | [`05_reasoning_mode.py`](examples/zh-cn/05_reasoning_mode.py) | `no_think` 与 `high` 推理模式对比。 |
| [错误处理与重试](examples/zh-cn/06_error_handling_retry.md) | [`06_error_handling_retry.py`](examples/zh-cn/06_error_handling_retry.py) | 超时、限流、网络错误的指数退避重试。 |

`examples/` 中的每个 `.md` 文件都包含完整请求、响应解析说明和示例输出。

## 7. 常见错误与排查

| 现象 | 可能原因 | 修复方式 |
| --- | --- | --- |
| `Connection refused`, `Name or service not known` | 服务未运行，或 `HY3_BASE_URL` 错误。 | 检查主机/端口，并运行 `curl ${HY3_BASE_URL}/models`。 |
| HTTP `401` / `403` | 网关或代理中的 API key 不匹配。 | 使用正确的 `HY3_API_KEY`。本地服务通常使用 `EMPTY` 即可。 |
| HTTP `404` 或 `model not found` | 请求中的模型名与服务端 `--served-model-name` 不匹配。 | 设置 `HY3_MODEL=hy3` 或检查 `/v1/models`。 |
| chat template 相关 HTTP `400` | 缺少 chat template，或 chat template 不兼容。 | 使用 Hy3 tokenizer/chat template，或更新 serving 框架。 |
| 期望工具调用时 `tool_calls` 为空 | 未启用工具解析器、工具 schema 较弱，或 `tool_choice` 为 `none`。 | 在服务启动时启用工具解析器，设置 `tool_choice="auto"`，并提供清晰的 JSON schema。 |
| 工具参数格式错误 | 自动工具调用在所有模式下都未必能严格约束参数。 | 添加 `strict: true`，设置 `parallel_tool_calls=false`，执行工具前校验 JSON，并重试或要求模型重新生成。 |
| 缺少 `reasoning_content` | 服务端未启用 reasoning parser，或框架未单独暴露推理内容。 | 启用 Hy3/Hunyuan reasoning parser。仍可使用 `reasoning_effort` 控制模型行为。 |
| HTTP `429` | 网关、代理或服务端队列正在限流。 | 使用指数退避重试，降低并发，调低 `max_tokens`。 |
| HTTP `500` / CUDA OOM | 上下文过长、`max_tokens` 过高、并发请求过多或 GPU 内存不足。 | 降低并发，缩短上下文/最大 token，调整服务配置，或使用更大显存的 GPU。 |
| 客户端超时 | 首次请求、模型加载或长文本生成耗时过长。 | 增加 SDK 超时时间，调低 `max_tokens`，使用流式输出改善感知延迟。 |
