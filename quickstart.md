# Hy3 API Quickstart

本文档面向需要快速接入腾讯混元 Hy3 模型的开发者，提供基础配置、最小可运行示例、核心参数说明与常见报错排查。

---

## 1. 基础信息

### 1.1 Base URL

Hy3 通过腾讯云大模型服务平台 **TokenHub** 提供 OpenAI 兼容接口。

| 地域 | Base URL | 资源调度范围 |
| :--- | :--- | :--- |
| 广州（默认） | `https://tokenhub.tencentmaas.com/v1` | 中国大陆 |
| 新加坡 | `https://tokenhub-intl.tencentmaas.com/v1` | 全球 |

> 备用地址：广州 `https://tokenhub.tencentmaas.cn/v1`，新加坡 `https://tokenhub-intl.tencentmaas.cn/v1`。默认地址不可用时再切换。

完整请求路径示例：

```text
POST https://tokenhub.tencentmaas.com/v1/chat/completions
```

### 1.2 API Key

1. 登录 [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub)。
2. 进入 **API Key 管理** 页面，单击 **创建 API Key**。
3. 创建完成后复制 Key，通过 `Authorization: Bearer <API_KEY>` 请求头鉴权。
4. 若选择“限定范围”访问，请确保勾选 **Hy3** 模型。

> 请妥善保管 API Key，不要硬编码在仓库或前端代码中。

### 1.3 Model 名称

| 模型名称 | model 参数值 | 说明 |
| :--- | :--- | :--- |
| Hy3 | `hy3` | 正式版，推荐生产使用 |
| Hy3 preview | `hy3-preview` | 预览版 |

本仓库示例默认使用 `hy3`，如需体验 preview 版本，将示例中的 `model` 替换为 `hy3-preview` 即可。

### 1.4 速率限制

TokenHub 的速率限制与账户套餐、地域及模型相关，基本原则如下：

- **并发数**：默认单账号并发数较低（早期混元生文接口默认 5 并发）。Token Plan 套餐的并发随等级提升（Lite < Standard < Pro < Max）。
- **请求频率**：部分接口默认 20 次/秒，实际以控制台与套餐说明为准。
- **上下文与输出**：Hy3 支持 256K 上下文；最大输出长度请参见控制台模型详情页。

> 建议：正式压测前先在控制台查看当前账号的 **配额与限制**，并根据限制实现客户端重试与退避。

---

## 2. 最小可运行示例

### 2.1 curl

```bash
export HY3_API_KEY="your_api_key"

curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "请用一句话介绍 Hy3 模型。"}
    ],
    "temperature": 0.7,
    "max_tokens": 512
  }'
```

### 2.2 Python（openai SDK）

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请用一句话介绍 Hy3 模型。"},
    ],
    temperature=0.7,
    max_tokens=512,
)

print(response.choices[0].message.content)
```

示例输出：

```text
Hy3 是腾讯混元团队发布的 295B 总参数、21B 激活参数的 MoE 语言模型，支持 256K 长上下文与工具调用。
```

---

## 3. 参数说明

### 3.1 通用参数

| 参数 | 类型 | 说明 | 建议 |
| :--- | :--- | :--- | :--- |
| `model` | string | 模型 ID，如 `hy3`、`hy3-preview` | 生产环境使用 `hy3` |
| `messages` | array | 对话上下文，角色包括 `system`、`user`、`assistant`、`tool` | system 角色可选，若存在须放在最前面 |
| `temperature` | float | 采样温度，控制输出随机性，范围 `[0.0, 2.0]` | 日常对话 `0.7`，代码/数学可降至 `0.2` |
| `top_p` | float | 核采样概率阈值，范围 `[0.0, 1.0]` | 通常与 `temperature` 二选一使用 |
| `max_tokens` / `max_completion_tokens` | integer | 单次回复的最大 token 数 | 根据任务长度调整，避免过长浪费 |
| `stop` | string / array | 停止词，遇到指定字符串时停止生成 | 可用于控制输出格式 |
| `stream` | boolean | 是否流式返回，默认 `false` | 需要逐字显示时设为 `true` |
| `tools` | array | 工具声明列表，启用 Function Calling | 详见 [04_tool_calling](examples/ex04_tool_calling.md) |
| `tool_choice` | string / object | 控制模型是否调用工具 | `auto`（默认）、`none` 或强制指定某个工具 |

### 3.2 思考模式开关

Hy3 支持在最终回答前输出推理过程，通过 `thinking` 参数控制：

| 参数 | 取值 | 说明 |
| :--- | :--- | :--- |
| `thinking.type` | `"enabled"` | 开启思考模式，模型会先输出推理过程 |
| `thinking.type` | `"disabled"` | 关闭思考模式，直接输出答案（默认） |

使用 Python SDK 时，`thinking` 需要通过 `extra_body` 传入：

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "9.11 和 9.8 哪个更大？"}],
    extra_body={"thinking": {"type": "enabled"}},
)

msg = response.choices[0].message
if hasattr(msg, "reasoning_content"):
    print("思考过程:", msg.reasoning_content)
print("最终回答:", msg.content)
```

> 思考过程通过 `reasoning_content` 字段返回，与 `content` 同级。未进行工具调用时，下一轮对话无需将 `reasoning_content` 回传。

### 3.3 推理强度

部分平台与部署方式支持通过 `reasoning_effort` 控制推理强度：

| 取值 | 说明 |
| :--- | :--- |
| `no_think` | 极速响应，适合日常对话 |
| `low` | 轻量推理 |
| `high` | 深度推理，适合代码、数学、多步任务 |

自托管 vLLM/SGLang 常见用法：

```python
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}
```

TokenHub 官方接口优先使用 `thinking` 参数开关；推理强度细节以控制台与最新文档为准。

---

## 4. 常见报错排查

### 4.1 401 Unauthorized / 鉴权失败

- 检查 `Authorization` 请求头是否为 `Bearer <API_KEY>`。
- 确认 API Key 已创建且未过期。
- 若 Key 设置了“限定范围”，确认已勾选 Hy3 模型。

### 4.2 404 Not Found / 模型不存在

- 确认 `model` 字段值为 `hy3` 或 `hy3-preview`，不要写成 `hunyuan-hy3` 等旧名称。
- 确认 Base URL 末尾为 `/v1`，不要写成 `/v1/`（部分旧文档有尾部斜杠差异，TokenHub 以无斜杠为准）。

### 4.3 429 Too Many Requests / 限流

- 降低并发数，单账号默认并发有限。
- 实现指数退避重试（参见 [06_error_handling](examples/ex06_error_handling.md)）。
- 在控制台查看当前套餐的 RPM/TPM/并发配额。

### 4.4 请求超时

- 复杂任务或长上下文响应时间较长，建议设置合理的 `timeout`（如 60~120 秒）。
- 对于长文本生成，使用 `stream=True` 可更快获得首 token。

### 4.5 输出被截断

- 检查 `max_tokens` 是否设置过小。
- 检查 `finish_reason`：
  - `stop`：正常结束；
  - `length`：达到 `max_tokens` 上限；
  - `content_filter` / `sensitive`：触发内容审核。

### 4.6 reasoning_content 为空

- 确认已传入 `thinking: {"type": "enabled"}`。
- 使用 OpenAI SDK 时，由于字段未在类型中声明，需用 `getattr(msg, "reasoning_content", None)` 访问。

---

## 5. 下一步

- 查看 [examples](examples/) 目录，按场景学习完整示例：
  - [01_basic_chat](examples/ex01_basic_chat.md)：单轮与多轮对话
  - [02_streaming](examples/ex02_streaming.md)：流式请求与逐 chunk 解析
  - [03_latency_comparison](examples/ex03_latency_comparison.md)：首 token 时延与总耗时对比
  - [04_tool_calling](examples/ex04_tool_calling.md)：单次与多轮工具调用
  - [05_reasoning_mode](examples/ex05_reasoning_mode.md)：思考过程开关对比
  - [06_error_handling](examples/ex06_error_handling.md)：超时/限流/网络错误重试

---

## 参考文档

- [TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078)
- [语言模型调用概览](https://cloud.tencent.com/document/product/1823/130079)
- [深度思考](https://cloud.tencent.com/document/product/1823/131208)
