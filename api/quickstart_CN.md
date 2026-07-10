# Hy3 API Quickstart

5 分钟跑通第一次调用，半小时上手主要能力。

---

## 基本信息

| 项目 | 说明 |
|------|------|
| **Base URL** | `https://tokenhub.tencentmaas.com/v1`（国内）/ `https://tokenhub-intl.tencentmaas.com/v1`（国际） |
| **API Key** | 在 [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub) 创建，格式 `sk-xxx` |
| **模型名** | `hy3`（主模型）/ `hy3-preview`（预览版） |
| **上下文长度** | 256K tokens（输入上限 192K，输出上限 128K） |
| **协议** | OpenAI Chat Completions API 兼容 |

### 速率限制

| 层级 | 限制 |
|------|------|
| 默认并行 | 按 TokenHub 套餐等级动态调整（Lite < Standard < Pro < Max） |
| 超额响应 | HTTP 429 `tpm rate limit exceeded` |

### 计费（按量计费）

| 模型 | 输入 (¥/M tokens) | 输出 (¥/M tokens) | 缓存命中 (¥/M tokens) |
|------|-------------------|-------------------|----------------------|
| hy3 | 1.00 | 4.00 | 0.25 |
| hy3-preview | 1.20 | 4.00 | 0.40 |

---

## 前置条件

1. 注册 [腾讯云账号](https://cloud.tencent.com) 并完成实名认证
2. 开通 [TokenHub 服务](https://console.cloud.tencent.com/tokenhub)
3. 在 [API 密钥管理](https://console.cloud.tencent.com/tokenhub/apikey) 创建 API Key
4. 配置环境变量（推荐）：
    - 复制 `.env.example` 为 `.env` 并填入你的密钥和地址
    - 或直接设置环境变量：

```bash
export HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
export HY3_API_KEY="sk-xxxxxxxxxxxxxxxx"
export HY3_MODEL=hy3
```

---

## 最小可运行示例

### cURL

```bash
curl https://tokenhub.tencentmaas.com/v1/chat/completions \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "你好！请简单介绍一下你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0
  }'
```

### Python + OpenAI SDK

```bash
pip install openai python-dotenv
```

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)

response = client.chat.completions.create(
    model=os.getenv("HY3_MODEL", "hy3"),
    messages=[
        {"role": "user", "content": "你好！请简单介绍一下你自己。"},
    ],
    temperature=0.9,
    top_p=1.0,
)

print(response.choices[0].message.content)
```

---

## 参数说明

| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| `model` | string | — | `hy3`, `hy3-preview` | 模型标识 |
| `messages` | array | — | — | 对话消息列表（支持 system / user / assistant / tool role） |
| `temperature` | float | 1.0 | 0.0 – 2.0 | 采样温度，越高随机性越强 |
| `top_p` | float | 1.0 | 0.0 – 1.0 | 核采样概率阈值 |
| `max_tokens` | int | — | 1 – 131072 | 最大输出 token 数 |
| `stream` | bool | false | — | 是否流式输出（SSE） |
| `stop` | string / array | — | — | 停止序列，最多 4 个 |
| `tools` | array | — | — | 工具定义列表（Function Calling） |
| `tool_choice` | string / object | `"auto"` | `"auto"` / `"none"` / `"required"` | 工具调用策略 |
| `seed` | int | — | 1 – 10000 | 随机种子，用于复现 |
| `reasoning_effort` | string | `"no_think"` | `"no_think"` / `"low"` / `"medium"` / `"high"` | 思考模式开关，通过 `extra_body` 传入 |

### reasoning_effort 说明

`reasoning_effort` 通过 `extra_body` 参数传入，控制模型的思考深度：

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "..."}],
    extra_body={
        "chat_template_kwargs": {
            "reasoning_effort": "high"
        }
    },
)
```

| 取值 | 场景 |
|------|------|
| `"no_think"` | 默认。直接回复，适合日常对话、简单问答 |
| `"low"` | 轻度思考，适合轻度推理 |
| `"medium"` | 中等思考，平衡速度与深度 |
| `"high"` | 深度思考（完整 CoT），适合数学、编程、复杂推理 |

---

## 常见报错排查

| HTTP 状态 | 错误信息 | 原因 | 解决 |
|-----------|---------|------|------|
| 401 | `Unauthorized` | API Key 无效或未传 | 检查 `Authorization` 请求头格式为 `Bearer sk-...` |
| 403 | `Forbidden` | 账户未开通服务或余额不足 | 在控制台开通 TokenHub 并充值 |
| 429 | `tpm rate limit exceeded` | 超出速率限制 | 降低并发，或升级套餐；实现指数退避重试 |
| 429 | `insufficient quota` | 账户配额用尽 | 检查套餐余量，或切换按量计费 |
| 400 | `invalid model` | 模型名错误 | 确认使用 `hy3` 或 `hy3-preview` |
| 400 | `invalid messages format` | 消息格式错误 | 确保 `messages` 为合法 JSON 数组，role 取值正确 |
| 408 / 504 | `Request timed out` | 请求超时 | 增大超时时间，或检查网络连接 |
| 500 | `Internal Server Error` | 服务端异常 | 稍后重试，若持续请联系技术支持 |

---

## 下一步

查看 [examples](./examples) 目录中的完整示例：

| 示例 | 说明 |
|------|------|
| [01 - Basic Chat](./examples/01_basic_chat) | 单轮 / 多轮对话 |
| [02 - Streaming](./examples/02_streaming) | 流式请求与逐 chunk 解析 |
| [03 - Non-streaming vs Streaming](./examples/03_nonstreaming_vs_streaming) | 首 token 时延与总耗时对比 |
| [04 - Tool Calling](./examples/04_tool_calling) | 一次调用 + 多轮工具循环 |
| [05 - Reasoning Mode](./examples/05_reasoning_mode) | 思考过程开 / 关对比 |
| [06 - Error Handling & Retry](./examples/06_error_handling_retry) | 超时 / 限流 / 网络错误的重试与退避 |

---

## 参考链接

- [TokenHub API 文档](https://cloud.tencent.com/document/product/1823/130078)
- [Hy3 TokenHub 接入指南](https://cloud.tencent.com/document/product/1823/132252)
- [定价详情](https://cloud.tencent.com/document/product/1823/130055)
- [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub)
