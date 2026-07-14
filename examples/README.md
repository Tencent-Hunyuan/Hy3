# Hy3 API Quickstart

> 5 分钟跑通第一次调用，半小时上手主要能力

## 1. 基础信息

| 项目 | 说明 |
|------|------|
| **API 风格** | OpenAI 兼容（直接使用 `openai` Python SDK） |
| **Base URL** | 自部署：`http://127.0.0.1:8000/v1`；云端：见 [AI Studio](https://aistudio.tencent.com/) |
| **API Key** | 自部署：任意字符串（如 `e2b_000000`）；云端：在 AI Studio 获取 |
| **Model** | `"hy3"` |
| **推荐参数** | `temperature=0.9`, `top_p=1.0` |
| **上下文长度** | 256K tokens |

## 2. 最小可运行示例

### curl

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [redacted]" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "你好！请简单介绍一下你自己。"}],
    "temperature": 0.9,
    "top_p": 1.0
  }'
```

### Python (OpenAI SDK)

```bash
pip install openai
```

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key=[redacted])

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好！请简单介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
)
print(response.choices[0].message.content)
```

完整代码见 [`examples/01-basic-chat.py`](examples/01-basic-chat.py)

## 3. 核心参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model` | string | `"hy3"` | 模型名称 |
| `messages` | list | 必填 | 对话消息列表，支持 system/user/assistant/tool |
| `temperature` | float | `0.9` | 采样温度，越高越随机（0-2） |
| `top_p` | float | `1.0` | 核采样概率阈值 |
| `max_tokens` | int | 自动 | 最大生成 token 数 |
| `stop` | string/list | 无 | 停止词 |
| `tools` | list | 无 | 工具定义（Function Calling） |
| `tool_choice` | string/object | `"auto"` | 工具选择策略 |
| `stream` | bool | `false` | 是否流式输出 |
| `reasoning_effort` | string | `"no_think"` | 思考模式：`"no_think"` / `"low"` / `"high"`（通过 `extra_body` 传入） |

### 思考模式（Reasoning Mode）

Hy3 支持三种思考模式，通过 `extra_body` 传入：

```python
# 快速回复（默认）
extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}

# 轻度思考
extra_body={"chat_template_kwargs": {"reasoning_effort": "low"}}

# 深度推理（适合数学、编程、复杂逻辑）
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}
```

完整对比见 [`examples/05-reasoning.py`](examples/05-reasoning.py)

## 4. 常见报错排查

| 错误 | 原因 | 解决 |
|------|------|------|
| `Connection refused` | 服务未启动或端口错误 | 检查 vLLM/SGLang 是否启动，确认端口为 8000 |
| `401 Unauthorized` | API Key 错误 | 自部署时 API Key 为任意字符串，确认请求头正确 |
| `model 'hy3' not found` | 模型名错误或未加载 | 确认启动时 `--served-model-name hy3` |
| `context length exceeded` | 输入超过 256K | 截断历史消息或减少输入 |
| `rate limit exceeded` | 请求过于频繁 | 增加请求间隔，实现指数退避重试 |
| `connection timeout` | 网络延迟或服务过载 | 设置 `timeout` 参数，使用重试机制 |

## 5. Examples 目录

| 序号 | 文件 | 内容 |
|------|------|------|
| 01 | `01-basic-chat.py` | 单轮 + 多轮对话 |
| 02 | `02-streaming.py` | 流式请求 + 逐 chunk 解析 |
| 03 | `03-latency-comparison.py` | 非流式 vs 流式 首 token 时延对比 |
| 04 | `04-tool-calling.py` | Tool Calling：一次调用 + 多轮工具循环 |
| 05 | `05-reasoning.py` | 思考模式开关对比（no_think vs high） |
| 06 | `06-error-handling.py` | 超时/限流/网络错误的重试与退避 |

每个 example 包含完整的请求、响应解析和示例输出。
