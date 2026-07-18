# Hy3 API Quickstart

本文说明如何通过 OpenAI 兼容接口调用 Hy3：完成首次请求，并快速上手常用能力。

Hy3 可在以下环境使用：

- **本地部署**：使用 vLLM / SGLang 提供服务（详见仓库 [README](./README.md) Deployment）
- **云端**：腾讯云 [TokenHub](https://cloud.tencent.com/product/tokenhub) 等 OpenAI 兼容网关

配套示例见 `examples/`。连接信息通过环境变量配置，**不要将 API Key 写入代码或提交到 Git 仓库**。

---

## 1. 基础信息

| 项 | 本地部署（与官方 README 默认一致） | 腾讯云 TokenHub（以控制台为准） |
|----|-----------------------------------|-------------------------------|
| **Base URL** | `http://127.0.0.1:8000/v1` | `https://tokenhub.tencentmaas.com/v1` |
| **API Key** | `EMPTY`（本地占位） | 控制台创建的 API Key |
| **Model** | `hy3` | `hy3`（或控制台显示的 Model ID） |
| **协议** | OpenAI Chat Completions | 同左 |
| **鉴权** | `Authorization: Bearer <API_KEY>` | 同左 |

### 环境变量

| 变量 | 含义 | 示例 |
|------|------|------|
| `HY3_BASE_URL` | API 根路径（含 `/v1`） | `https://tokenhub.tencentmaas.com/v1` |
| `HY3_API_KEY` | 密钥 | （本地配置，勿入库） |
| `HY3_MODEL` | 模型 ID | `hy3` |

```bash
# Linux / macOS
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
export HY3_API_KEY="your-key"
export HY3_MODEL="hy3"
```

```powershell
# Windows PowerShell
$env:HY3_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
$env:HY3_API_KEY = "your-key"
$env:HY3_MODEL = "hy3"
```

### 速率与额度

- **本地**：受 GPU、并发与推理框架配置影响。
- **TokenHub**：以控制台额度、RPM/TPM 及套餐为准。
- 调试阶段建议使用较小的 `max_tokens`。

查询可用模型：`GET {BASE_URL}/models`。

---

## 2. 最小可运行示例

### 2.1 curl

```bash
curl -sS "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${HY3_MODEL:-hy3}\",
    \"messages\": [{\"role\": \"user\", \"content\": \"用一句话介绍你自己\"}],
    \"max_tokens\": 128,
    \"temperature\": 0.9,
    \"top_p\": 1.0
  }"
```

PowerShell：

```powershell
$headers = @{
  Authorization = "Bearer $env:HY3_API_KEY"
  "Content-Type" = "application/json"
}
$body = @{
  model = $env:HY3_MODEL
  messages = @(@{ role = "user"; content = "用一句话介绍你自己" })
  max_tokens = 128
  temperature = 0.9
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri "$env:HY3_BASE_URL/chat/completions" -Headers $headers -Body $body
```

### 2.2 Python（OpenAI SDK）

```bash
pip install openai
```

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)
model = os.environ.get("HY3_MODEL", "hy3")

resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "用一句话介绍你自己"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
)
print(resp.choices[0].message.content)
```

推荐参数（与仓库 README 一致）：`temperature=0.9`，`top_p=1.0`。

---

## 3. 主要参数

| 参数 | 作用 | 说明 |
|------|------|------|
| `temperature` | 采样温度 | 通用对话可用 `0.9` |
| `top_p` | 核采样 | 可用 `1.0` |
| `max_tokens` | 最大生成长度 | 按任务设置 |
| `stop` | 停止序列 | 可选 |
| `stream` | 流式输出 | 见 `examples/02_streaming` |
| `tools` / `tool_choice` | 工具调用 | 见 `examples/04_tool_calling` |
| 思考模式 | 快答 / 深度推理 | 见下文 |

### 思考模式

本地 vLLM / SGLang（与官方 README 一致）：

```python
extra_body = {
    "chat_template_kwargs": {
        "reasoning_effort": "no_think"  # 或 "low" / "high"
    }
}
resp = client.chat.completions.create(
    model=model,
    messages=messages,
    extra_body=extra_body,
)
```

| `reasoning_effort` | 含义 |
|--------------------|------|
| `no_think` | 直接回答 |
| `low` | 轻度思考 |
| `high` | 深度推理 |

不同网关字段可能不同；`examples/05_reasoning_mode.py` 提供兼容写法。以实际返回的 `content` / `reasoning_content` 为准。

### 工具调用

本地部署需启用 tool parser，例如：

- vLLM：`--tool-call-parser hy_v3 --enable-auto-tool-choice`
- SGLang：`--tool-call-parser hunyuan`

云端能力以平台文档为准。

---

## 4. 常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 连接失败 | 服务未启动或 Base URL 错误 | 检查端口；确认 URL 包含 `/v1` |
| `401` | Key 无效或未设置 | 检查 `HY3_API_KEY` |
| `404` / model not found | 模型名不一致 | 调用 `GET /v1/models` 核对 |
| 超时 | 冷启动或网络慢 | 增大 timeout；减小 `max_tokens` |
| `429` | 触发限流 | 指数退避重试（见 example 06） |
| `content` 为空 | 字段解析差异 | 打印完整 `message` |
| 无 `tool_calls` | 未启用 parser 或模型未调用工具 | 检查启动参数与 tools 定义 |

---

## 5. 示例索引

见 [`examples/README.md`](./examples/README.md)：

1. basic chat  
2. streaming  
3. non-stream vs stream latency  
4. tool calling  
5. reasoning mode  
6. error handling & retry  

---

## 6. 参考

- 本仓库 README（Quickstart / Deployment）
- [TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078)
- [混元调用指南](https://cloud.tencent.com/document/product/1823/132252)
