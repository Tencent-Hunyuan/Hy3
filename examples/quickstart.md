# Hy3 API 快速开始 / Quickstart

[中文](#中文) | [English](#english)

---

## 中文

本指南帮助你在 **5 分钟内** 完成第一次 Hy3 API 调用，并在 **半小时内** 掌握主要能力。

### 前置条件

- 已部署 Hy3 服务（参考 [部署指南](../README_CN.md#推理和部署)）
- Python 3.10+ 环境
- 安装 OpenAI SDK：`pip install openai>=1.0`
- （可选）安装 curl，用于命令行示例

---

### 基础信息

| 配置项 | 值 | 说明 |
|:---|:---|:---|
| Base URL | `http://<YOUR_SERVER_IP>:8000/v1` | API 服务地址，默认本地 `http://127.0.0.1:8000/v1` |
| API Key | `"EMPTY"` 或任意非空字符串 | 自部署场景无需真实密钥，填写任意值即可 |
| Model | `"hy3"` | 模型名称，与部署时 `--served-model-name` 参数保持一致 |
| 协议 | OpenAI 兼容 API | 支持 `/v1/chat/completions` 等标准接口 |

> **注意**：如使用云服务商托管的 Hy3 API，请将 Base URL 和 API Key 替换为服务商提供的值。

---

### 最小可运行示例

#### Python（OpenAI SDK）

```python
from openai import OpenAI

# 初始化客户端
client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",  # 自部署场景无需真实密钥
)

# 发送请求
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好！请简单介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

print(response.choices[0].message.content)
```

#### curl

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好！请简单介绍一下你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0
  }'
```

---

### 参数说明

#### 标准参数

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `model` | string | — | **必填**。模型名称，如 `"hy3"` |
| `messages` | list | — | **必填**。对话消息列表，每条包含 `role`（`system`/`user`/`assistant`）和 `content` |
| `temperature` | float | `0.9` | 控制生成随机性。推荐值 `0.9`，范围 `[0, 2]`，值越高输出越多样 |
| `top_p` | float | `1.0` | 核采样。推荐值 `1.0`，与 `temperature` 不建议同时修改 |
| `max_tokens` | int | `4096` | 最大生成 token 数。根据任务复杂度调整，上限受模型上下文长度（256K）限制 |
| `stop` | string / list | `null` | 停止生成的标记。如 `"stop": ["\n\n", "END"]`，遇到任一标记即停止 |
| `stream` | bool | `false` | 是否开启流式输出，详见 [流式示例](./02_streaming.md) |
| `tools` | list | `null` | 工具定义列表，详见 [工具调用示例](./04_tool_calling.md) |

#### 思考模式（Reasoning Mode）

通过 `extra_body` 传入，控制模型是否展示思维链：

| `reasoning_effort` 值 | 行为 | 适用场景 |
|:---|:---|:---|
| `"no_think"`（默认） | 直接输出结果，不展示思考过程 | 日常对话、简单问答 |
| `"low"` | 展示简要思考过程 | 中等复杂度任务 |
| `"high"` | 展示完整深度思维链 | 数学、编程、复杂推理 |

```python
# 开启深度思考
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "证明根号2是无理数"}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

> 详见 [思考模式示例](./05_reasoning_mode.md)

---

### 常见报错排查

| 错误信息 | 原因 | 解决方案 |
|:---|:---|:---|
| `Connection refused` | 服务未启动或端口错误 | 确认 vLLM/SGLang 服务已启动，检查端口配置 |
| `The model 'xxx' does not exist` | 模型名不匹配 | 确认 `model` 参数与部署时的 `--served-model-name` 一致 |
| `API rate limit reached` | 请求频率超限 | 降低并发请求数，或实现退避重试（参考 [错误处理示例](./06_error_handling.md)） |
| `Request timed out` | 生成时间过长或网络问题 | 适当减小 `max_tokens`，或增加客户端超时时间 |
| `Invalid value for 'messages'` | 消息格式错误 | 检查每条消息是否包含 `role` 和 `content` 字段 |
| `CUDA out of memory` | GPU 显存不足 | Hy3 总参数 295B，建议使用 8×H20-3e 或同等显存配置 |
| `Tool call parse error` | 工具调用格式错误 | 确认 `tools` 参数格式符合 OpenAI 规范，参考 [工具调用示例](./04_tool_calling.md) |

---

## English

This guide helps you make your **first Hy3 API call in 5 minutes** and master the main capabilities within **30 minutes**.

### Prerequisites

- Hy3 service deployed (see [Deployment Guide](../README.md#deployment))
- Python 3.10+ environment
- OpenAI SDK installed: `pip install openai>=1.0`
- (Optional) curl for command-line examples

---

### Basic Information

| Config | Value | Description |
|:---|:---|:---|
| Base URL | `http://<YOUR_SERVER_IP>:8000/v1` | API server address, default `http://127.0.0.1:8000/v1` |
| API Key | `"EMPTY"` or any non-empty string | Not required for self-hosted deployment |
| Model | `"hy3"` | Must match `--served-model-name` used at launch |
| Protocol | OpenAI-compatible API | Supports `/v1/chat/completions` and other standard endpoints |

> **Note**: If using a cloud-hosted Hy3 API, replace the Base URL and API Key with your provider's values.

---

### Minimal Runnable Examples

#### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "Hello! Can you briefly introduce yourself?"},
    ],
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

print(response.choices[0].message.content)
```

#### curl

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "Hello! Can you briefly introduce yourself?"}
    ],
    "temperature": 0.9,
    "top_p": 1.0
  }'
```

---

### Parameter Reference

#### Standard Parameters

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `model` | string | — | **Required**. Model name, e.g. `"hy3"` |
| `messages` | list | — | **Required**. List of messages with `role` (`system`/`user`/`assistant`) and `content` |
| `temperature` | float | `0.9` | Sampling randomness. Recommended `0.9`, range `[0, 2]` |
| `top_p` | float | `1.0` | Nucleus sampling. Recommended `1.0`. Avoid changing together with `temperature` |
| `max_tokens` | int | `4096` | Max tokens to generate. Adjust based on task complexity |
| `stop` | string / list | `null` | Stop sequences, e.g. `"stop": ["\n\n", "END"]` |
| `stream` | bool | `false` | Enable streaming output, see [Streaming Example](./02_streaming.md) |
| `tools` | list | `null` | Tool definitions, see [Tool Calling Example](./04_tool_calling.md) |

#### Reasoning Mode

Control chain-of-thought visibility via `extra_body`:

| `reasoning_effort` Value | Behavior | Use Case |
|:---|:---|:---|
| `"no_think"` (default) | Direct output, no reasoning trace | Casual chat, simple Q&A |
| `"low"` | Brief reasoning shown | Medium complexity tasks |
| `"high"` | Full deep chain-of-thought | Math, coding, complex reasoning |

```python
# Enable deep reasoning
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Prove that sqrt(2) is irrational"}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

> See [Reasoning Mode Example](./05_reasoning_mode.md)

---

### Troubleshooting

| Error | Cause | Solution |
|:---|:---|:---|
| `Connection refused` | Server not running or wrong port | Verify vLLM/SGLang is running; check port config |
| `The model 'xxx' does not exist` | Model name mismatch | Ensure `model` matches `--served-model-name` |
| `API rate limit reached` | Too many requests | Reduce concurrency or implement retry with backoff ([Error Handling](./06_error_handling.md)) |
| `Request timed out` | Generation too long or network issue | Reduce `max_tokens` or increase client timeout |
| `Invalid value for 'messages'` | Malformed messages | Ensure each message has `role` and `content` fields |
| `CUDA out of memory` | Insufficient GPU memory | Hy3 has 295B params; use 8×H20-3e or equivalent |
| `Tool call parse error` | Invalid tool definition format | Verify `tools` follows OpenAI spec ([Tool Calling](./04_tool_calling.md)) |

---

## Examples 目录

| # | 示例 | 文件 |
|:---|:---|:---|
| 1 | 基础对话（单轮/多轮） | [01_basic_chat.md](./01_basic_chat.md) / [01_basic_chat.py](./01_basic_chat.py) |
| 2 | 流式输出 | [02_streaming.md](./02_streaming.md) / [02_streaming.py](./02_streaming.py) |
| 3 | 流式 vs 非流式对比 | [03_streaming_vs_non_streaming.md](./03_streaming_vs_non_streaming.md) / [03_streaming_vs_non_streaming.py](./03_streaming_vs_non_streaming.py) |
| 4 | 工具调用 | [04_tool_calling.md](./04_tool_calling.md) / [04_tool_calling.py](./04_tool_calling.py) |
| 5 | 思考模式 | [05_reasoning_mode.md](./05_reasoning_mode.md) / [05_reasoning_mode.py](./05_reasoning_mode.py) |
| 6 | 错误处理与重试 | [06_error_handling.md](./06_error_handling.md) / [06_error_handling.py](./06_error_handling.py) |
