# Hy3 API 快速开始

本指南帮助你在 **5 分钟内**完成第一次 Hy3 API 调用，并在 **30 分钟内**上手主要能力。

Hy3 提供 **OpenAI 兼容** 的 Chat Completions API，可直接使用 `openai` Python SDK、`curl` 或任意兼容客户端。

两种调用路径：

| 路径 | 适用场景 | Base URL |
|:---|:---|:---|
| **A. 腾讯云 TokenHub（推荐首次调用）** | 无本地 GPU，申请 API Key 即可 | `https://tokenhub.tencentmaas.com/v1` |
| **B. 自建 vLLM / SGLang** | 私有化 / 离线 / 完全可控 | 默认 `http://127.0.0.1:8000/v1` |

可运行示例（`.py` / `.md` / `.ipynb`，中英双语）：见 [`examples/cn/`](./examples/cn/) 与 [`examples/en/`](./examples/en/)。

---

## 目录

- [1. 基础信息](#1-基础信息)
- [2. 最小可运行示例（5 分钟）](#2-最小可运行示例5-分钟)
- [3. 参数说明](#3-参数说明)
- [4. 常见报错排查](#4-常见报错排查)
- [5. 下一步](#5-下一步)

---

## 1. 基础信息

### 1.1 托管 API — TokenHub

| 项目 | 值 | 说明 |
|:---|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` | OpenAI 兼容端点 |
| API Key | 你的 TokenHub Key | 在控制台创建 / 管理；**切勿提交到仓库** |
| 模型名（model） | `hy3` | 除非控制台另有 served name，否则固定用 `hy3` |
| 协议 | OpenAI Chat Completions | `/v1/chat/completions` |
| 上下文长度 | 256K | 单次请求输入 + 输出 token 上限 |

**速率限制（云端）：** QPS / TPM / 并发由云产品配置。遇到 HTTP `429` 请退避（优先遵守 `Retry-After`）并降低并发，具体配额以官方文档为准。

### 1.2 自建 — vLLM / SGLang

| 项目 | 值 | 说明 |
|:---|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` | 本地默认监听地址 + `/v1` |
| API Key | `EMPTY` | 本地通常不校验密钥，任意非空字符串即可 |
| 模型名（model） | `hy3` | 必须与 `--served-model-name hy3` 一致 |
| 硬件 | 8 卡 GPU（推荐 H20-3e） | 295B MoE 需要较大显存 |
| 工具解析器 | vLLM: `hy_v3` / SGLang: `hunyuan` | 工具调用必需 |
| 思考解析器 | vLLM: `hy_v3` / SGLang: `hunyuan` | 用于返回 `reasoning_content` |

**速率限制（本地）：** 无统一硬限。实际并发由 vLLM/SGLang 配置与显存决定；256K 长上下文会显著降低可并发数。

### 1.3 示例使用的环境变量

| 环境变量 | 默认值 | 说明 |
|:---|:---|:---|
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI 兼容 Base URL |
| `HY3_API_KEY` | `EMPTY` | API Key |
| `HY3_MODEL` | `hy3` | 模型名 |
| `HY3_TIMEOUT` | `120` | 客户端超时（秒） |

可参考 [`examples/.env.example`](./examples/.env.example)。不要提交真实密钥。

---

## 2. 最小可运行示例（5 分钟）

### 2.1 路径 A — TokenHub（无需本地 GPU）

```bash
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
export HY3_API_KEY="sk-xxxxxxxx"   # 替换为你的 Key
export HY3_MODEL="hy3"
```

**curl**

```bash
curl -X POST "$HY3_BASE_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "用一句话介绍一下你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "thinking": {"type": "disabled"},
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

**Python（OpenAI SDK）**

```bash
pip install openai
```

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"),
    api_key=os.environ["HY3_API_KEY"],  # TokenHub 必填
)

response = client.chat.completions.create(
    model=os.environ.get("HY3_MODEL", "hy3"),
    messages=[{"role": "user", "content": "用一句话介绍一下你自己。"}],
    temperature=0.9,
    top_p=1.0,
    # 云端 + 本地双兼容的思考开关：
    extra_body={
        "thinking": {"type": "disabled"},  # TokenHub
        "chat_template_kwargs": {"reasoning_effort": "no_think"},  # vLLM / SGLang
    },
)

print(response.choices[0].message.content)
```

期望响应结构（内容由模型生成）：

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

### 2.2 路径 B — 本地 vLLM / SGLang

1. 按仓库 [README 部署章节](./README_CN.md#推理和部署) 启动服务（`--served-model-name hy3`，端口 `8000`）。
2. 确认：`curl http://127.0.0.1:8000/v1/models`
3. 使用 `base_url=http://127.0.0.1:8000/v1`、`api_key="EMPTY"` 调用。

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "用一句话介绍一下你自己。"}],
    temperature=0.9,
    top_p=1.0,
    extra_body={
        "thinking": {"type": "disabled"},
        "chat_template_kwargs": {"reasoning_effort": "no_think"},
    },
)
print(response.choices[0].message.content)
```

> **SDK 说明：** OpenAI Python SDK 中厂商扩展字段放在 `extra_body`；原始 `curl`/HTTP 则把 `thinking` 与 `chat_template_kwargs` 放在 JSON 顶层。

---

## 3. 参数说明

### 3.1 temperature

| 字段 | 内容 |
|:---|:---|
| 含义 | 采样随机性。越高越发散，越低越确定。 |
| 范围 | `0.0` ~ `2.0` |
| 推荐 | **`0.9`**（Hy3 官方推荐） |

### 3.2 top_p

| 字段 | 内容 |
|:---|:---|
| 含义 | 核采样阈值。 |
| 范围 | `0.0` ~ `1.0` |
| 推荐 | **`1.0`** |

### 3.3 max_tokens

| 字段 | 内容 |
|:---|:---|
| 含义 | 单次生成 token 上限（不含输入）。 |
| 范围 | 不超过上下文长度减去输入（总 256K） |
| 推荐 | 闲聊 512~2048；长文 4096~8192；`high` 思考 ≥ 8192 |

### 3.4 stop

| 字段 | 内容 |
|:---|:---|
| 含义 | 停止序列，匹配后立即停止生成。 |
| 类型 | 字符串或字符串数组 |

### 3.5 tools（工具调用）

使用 OpenAI `tools` JSON Schema 声明工具。模型可能返回 `tool_calls`，客户端执行后以 `role=tool` 回传结果。

**自建服务必须开启工具解析器：**

- vLLM: `--tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice`
- SGLang: `--tool-call-parser hunyuan --reasoning-parser hunyuan`

有界多轮工具循环示例：[`examples/cn/04_tool_calling.py`](./examples/cn/04_tool_calling.py)。

### 3.6 思考模式开关

建议**同时发送两种参数**，使同一代码兼容 TokenHub 与本地：

| 模式 | TokenHub（`thinking.type`） | 本地（`reasoning_effort`） | 适用场景 |
|:---|:---|:---|:---|
| 关闭 | `disabled` | `no_think` | 日常对话，最低时延 |
| 轻度 | `enabled` | `low` | 轻度结构化 / 多约束 |
| 深度 | `enabled` | `high` | 数学、代码、复杂推理 |

```python
extra_body = {
    "thinking": {"type": "enabled"},  # TokenHub
    "chat_template_kwargs": {"reasoning_effort": "high"},  # 本地
}
# 开启后思维链可能出现在 message.reasoning_content
# （本地需 --reasoning-parser；TokenHub 由服务端分离）
```

完整对比：[`examples/cn/05_reasoning_mode.py`](./examples/cn/05_reasoning_mode.py)。

---

## 4. 常见报错排查

### 4.1 连接失败

**现象：** `Connection refused` / `Failed to connect`。

- TokenHub：检查网络 / 代理 / DNS，确认 Base URL。
- 本地：服务未启动、端口错误或模型仍在加载。查看启动日志并 `curl .../v1/models`。

### 4.2 鉴权失败（401）

- TokenHub：Key 为空 / 错误 / 过期；确保 `Authorization: Bearer <key>`。
- 本地：使用任意非空 Key（如 `EMPTY`），避免 `api_key=None`。

### 4.3 模型未找到（404 / 400）

- 请求中的 `model` 必须与 served name（`hy3`）一致。
- 列出模型：`GET {base_url}/models`。

### 4.4 超时

- 增大客户端 `timeout`（示例默认 120s）。
- `high` 思考与长上下文需要更长时间与更大 `max_tokens`。
- 服务端排队严重时降低并发。

### 4.5 限流（429）

- 指数退避；若响应带 `Retry-After` 请遵守。
- 降低客户端并发；云端场景核对配额。
- 示例：[`examples/cn/06_error_handling_retry.py`](./examples/cn/06_error_handling_retry.py)。

### 4.6 开启思考后 `reasoning_content` 仍为空

- TokenHub：确认发送了 `thinking: {type: enabled}`。
- 本地 vLLM：启动加 `--reasoning-parser hy_v3`
- 本地 SGLang：启动加 `--reasoning-parser hunyuan`

### 4.7 工具调用未触发

**现象：** 已发送 `tools`，但 `message.tool_calls` 为 `None`。

- 本地 vLLM：启动加 `--tool-call-parser hy_v3 --enable-auto-tool-choice`。
- 本地 SGLang：启动加 `--tool-call-parser hunyuan`。
- 确认 `tool_choice` 为 `auto`（或指定具体工具）；`"none"` 会禁用工具调用。
- 部分 chat template 要求 `tools` 通过 `extra_body` 而非顶层传入 —— 不确定时查阅服务端文档。
- 示例：[`examples/cn/04_tool_calling.py`](./examples/cn/04_tool_calling.py)。

### 4.8 Chat template 缺失 / 异常

**现象：** `Chat template not set` / `Apply chat template failed` / 输出乱码。

- served 模型目录必须包含有效的 `chat_template.jinja`（或带模板的 tokenizer 配置）。
- 从自定义路径加载权重时，重新确认 tokenizer 文件齐全。
- 思考模式依赖模板支持 `reasoning_effort` —— 否则 `reasoning_content` 恒为空。
- 避免手动拼接 prompt，始终通过 `messages` API 调用。

### 4.9 CUDA 显存不足（本地部署）

**现象：** 服务端日志 `CUDA out of memory` / 请求返回 500 / 卡住。

- Hy3 需要 8 张 GPU（如 H20-3e），单张 24GB 卡无法承载。
- 降低 `--max-model-len` / `--max-num-seqs` / `gpu-memory-utilization`。
- 关闭其他 GPU 进程（`nvidia-smi`）；全权重部署 TP=8 是硬性要求。
- 可尝试量化方案（如有提供），或显存不足时改用云端 TokenHub API。
- 长上下文请求谨慎提高 `max_tokens` —— 输出同样占用 KV cache。

---

## 5. 下一步

| 目标 | 链接 |
|:---|:---|
| 中文示例（py / md / ipynb） | [`examples/cn/`](./examples/cn/) |
| 英文示例 | [`examples/en/`](./examples/en/) |
| 共享工具与离线测试 | [`examples/common.py`](./examples/common.py)、[`examples/tests/`](./examples/tests/) |
| 完整部署（vLLM / SGLang） | [README 推理和部署](./README_CN.md#推理和部署) |
| 微调 | [`finetune/README_CN.md`](./finetune/README_CN.md) |
| English quickstart | [`quickstart.md`](./quickstart.md) |

```bash
pip install -r examples/requirements.txt
# 可选：离线测试（无需 API Key）
pip install -r examples/requirements-dev.txt
pytest examples/tests -q
```

反馈邮箱：`hunyuan_opensource@tencent.com`。
