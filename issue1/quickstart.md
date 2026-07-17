# Hy3 API Quickstart

> 面向开发者的快速入门指南：**5 分钟跑通第一次调用，半小时掌握主要能力。**

Hy3 是腾讯混元团队研发的 295B MoE 大模型（21B 激活参数），通过 TokenHub 平台提供 OpenAI 兼容的 API 接口。本文档帮助你快速接入并验证 Hy3 的核心能力。

---

## 0. 准备工作

### 获取 API Key

1. 访问 [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey)
2. 登录腾讯云账号，点击「创建 API Key」
3. 复制 API Key 备用

> 💡 **新用户福利**：在 TokenHub「模型广场」可领取 Hy3 Preview **100 万 Tokens** 免费体验包（90 天有效）。

### 配置环境

```bash
# 克隆仓库并进入示例目录
cd issue1

# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入你的 API Key
# HY3_API_KEY=sk-xxxxxxxx
```

### 安装依赖

```bash
pip install "openai>=1.0.0" python-dotenv
```

---

## 1. 基础信息

| 项目 | 值 | 说明 |
|:---|:---|:---|
| **Base URL** | `https://tokenhub.tencentmaas.com/v1` | TokenHub OpenAI 兼容端点 |
| **API Key** | `sk-xxxxxxxx` | 从 TokenHub 控制台获取 |
| **Model** | `hy3-preview`（推荐）或 `hy3` | `hy3-preview` 支持 256K 上下文 |
| **Endpoint** | `/chat/completions` | 完整 URL: `${BASE_URL}/chat/completions` |
| **速率限制** | 视套餐而定 | Token Plan 套餐有不同并发限制，详见控制台 |

### 模型选择建议

| 模型 | 上下文 | 适用场景 |
|:---|:---|:---|
| `hy3-preview` | 256K | **推荐**。日常开发、长文档处理、复杂推理 |
| `hy3` | 128K | 正式版，生产环境 |

---

## 2. 最小可运行示例

### curl

```bash
# 设置环境变量
export HY3_API_KEY="你的API_Key"
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"

curl "${HY3_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3-preview",
    "messages": [
      {"role": "user", "content": "你好！请用一句话介绍你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 128
  }'
```

典型返回：

```json
{
  "id": "chatcmpl-xxxxxxxx",
  "object": "chat.completion",
  "created": 1783400000,
  "model": "hy3-preview",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！我是混元，腾讯开发的大型语言模型，擅长代码、推理和长文本处理任务。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 22,
    "total_tokens": 37
  }
}
```

### Python (OpenAI SDK)

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url=os.getenv("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"),
)

response = client.chat.completions.create(
    model="hy3-preview",
    messages=[
        {"role": "user", "content": "你好！请用一句话介绍你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
)

print(response.choices[0].message.content)
```

> ⚠️ **注意**：TokenHub 接口使用标准 OpenAI 协议，**不要**发送 `chat_template_kwargs` 等 Hy3 本地部署专用参数，否则会报错。

---

## 3. 核心参数说明

| 参数 | 类型 | 默认/建议 | 说明 |
|:---|:---|:---|:---|
| `temperature` | `number` | `0.9` | 采样温度。`0.1-0.3` 适合确定性任务（代码、数学），`0.7-0.9` 适合创意生成 |
| `top_p` | `number` | `1.0` | 核采样阈值。与 temperature 二选一调节即可 |
| `max_tokens` | `integer` | `128-4096` | 最大生成 token 数。过小会截断 (finish_reason=`length`)，过大增加延迟 |
| `stop` | `string/array` | 无 | 停止序列。命中后立即停止生成，适用于格式化输出 |
| `tools` | `array` | 无 | Function calling 工具定义，需配合 `tool_choice` 使用 |
| `stream` | `boolean` | `false` | 是否流式返回。交互式场景设为 `true` 可降低首字延迟感知 |
| `reasoning_effort` | `string` | `no_think` | **Hy3 思考模式**。`no_think` 直接回答，`low` 中等推理，`high` 深度思维链（通过 `extra_body.chat_template_kwargs` 传入，仅本地部署支持） |

### 思考模式（Reasoning Mode）最佳实践

Hy3 的思考模式是其核心特性之一，不同 effort 级别对应不同场景：

| effort | 适用场景 | 预期行为 |
|:---|:---|:---|
| `no_think` | 日常对话、简单问答、信息检索 | 直接输出，延迟最低 |
| `low` | 有一定复杂度的推理、格式化输出 | 简短内部思考后输出 |
| `high` | 数学证明、复杂编程、多步推理 | 完整思维链，延迟最高但质量最好 |

> ⚠️ **TokenHub 云端 API 的思考模式支持**：部分云服务可能不直接暴露 `reasoning_content` 字段。若需要完整思考过程，建议本地部署 vLLM/SGLang 并使用 `chat_template_kwargs.reasoning_effort` 参数。

---

## 4. Examples 概览

示例代码位于 `issue1/examples/` 目录下，每个示例包含 `.py`（可运行脚本）和 `.md`（说明文档）：

| # | 示例 | 文件 | 学习要点 |
|:---|:---|:---|:---|
| 1 | Basic Chat | `basic_chat.py/.md` | 单轮/多轮对话，请求构造与响应解析 |
| 2 | Streaming | `streaming.py/.md` | 流式请求，逐 chunk 解析 delta 字段 |
| 3 | Latency Compare | `latency_compare.py/.md` | 非流式 vs 流式首 token 时延对比 |
| 4 | Tool Calling | `tool_calling.py/.md` | 函数调用定义、参数解析、多轮工具循环 |
| 5 | Reasoning Mode | `reasoning_mode.py/.md` | `no_think` vs `high` 思考模式对比 |
| 6 | Retry & Error | `retry.py/.md` | 指数退避重试、可重试/不可重试错误分类 |

### 运行所有示例

```bash
cd issue1
pip install "openai>=1.0.0" python-dotenv

# 确保 .env 已配置 API Key
python examples/basic_chat.py
python examples/streaming.py
python examples/latency_compare.py
python examples/tool_calling.py
python examples/reasoning_mode.py
python examples/retry.py
```

---

## 5. 常见报错排查

| 现象 | 可能原因 | 解决方案 |
|:---|:---|:---|
| `401 Unauthorized` | API Key 无效或未设置 | 检查 `.env` 中 `HY3_API_KEY`；确认 TokenHub 控制台中 Key 状态正常 |
| `403 Forbidden` | API Key 权限不足或额度耗尽 | 检查套餐余量，确认 Key 有调用对应模型的权限 |
| `404 model not found` | 模型名错误 | 确认 model 参数为 `hy3-preview` 或 `hy3` |
| `ConnectionError` / `ConnectTimeout` | 网络不通 | 检查是否需代理；确认 `HY3_BASE_URL` 正确 |
| `429 Too Many Requests` | 超过速率限制 | 降低并发，实现指数退避重试（参考 retry 示例） |
| `finish_reason="length"` | `max_tokens` 设置过小 | 增大 `max_tokens` 或精简 prompt |
| `context_length_exceeded` | 输入超过模型上下文限制 | 缩短历史消息，或换用 `hy3-preview`（256K 上下文） |
| 响应内容为空 | `reasoning_effort` 模式下思考占满 token 预算 | 增大 `max_tokens`；非推理场景使用 `no_think` |
| tool call 未触发 | 模型判断不需要调工具，或 tool schema 不清晰 | 优化 tool description；必要时设置 `tool_choice="required"` |
| `chat_template_kwargs` 报错 | 将本地部署专用参数发给了云 API | TokenHub 云端不要发送 `chat_template_kwargs`，仅本地 vLLM/SGLang 支持 |

---

## 6. 从本地部署迁移到 TokenHub 云 API

如果你之前使用本地 vLLM/SGLang 部署，切换到 TokenHub 只需修改：

```python
# 本地部署 (vLLM/SGLang)
client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",  # 改为 TokenHub URL
    api_key="EMPTY",                       # 改为真实 API Key
)
# 去掉 extra_body={"chat_template_kwargs": ...}  # 云 API 不支持

# TokenHub 云 API
client = OpenAI(
    base_url="https://tokenhub.tencentmaas.com/v1",
    api_key=os.getenv("HY3_API_KEY"),
)
```

---

## 7. 下一步

1. 从 `examples/basic_chat.py` 开始跑通第一个请求
2. 根据业务需求依次验证 streaming、tool calling、reasoning mode
3. 将 retry 策略集成到生产代码中
4. 阅读 [Hy3 官方文档](https://github.com/Tencent-Hunyuan/Hy3) 了解模型微调和 RL 训练

---

## 参考链接

- [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/)
- [Hy3 GitHub 仓库](https://github.com/Tencent-Hunyuan/Hy3)
- [OpenAI Python SDK 文档](https://github.com/openai/openai-python)
- [腾讯混元大模型文档](https://cloud.tencent.com/document/product/1729)
