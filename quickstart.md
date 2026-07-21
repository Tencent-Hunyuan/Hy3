# Hy3 API 快速开始（本地部署）

> **5 分钟跑通第一次调用，半小时上手主要能力。** 本文以本地部署（vLLM / SGLang）为主线，调用方式基于 OpenAI 兼容 SDK。

## 目录

- [1. 准备环境](#1-准备环境)
- [2. 设置环境变量](#2-设置环境变量)
- [3. 用 curl 完成第一次调用](#3-用-curl-完成第一次调用)
- [4. 用 Python OpenAI SDK 调用](#4-用-python-openai-sdk-调用)
- [5. 参数说明](#5-参数说明)
- [6. 思考模式（Reasoning Mode）](#6-思考模式reasoning-mode)
- [7. 工具调用（Tool Calling）](#7-工具调用tool-calling)
- [8. 速率限制与重试](#8-速率限制与重试)
- [9. 常见错误排查](#9-常见错误排查)
- [10. 示例索引](#10-示例索引)

---

## 1. 准备环境

1. 安装依赖（Python ≥ 3.10）：
   ```bash
   python -m pip install -U openai
   # 或用仓库自带的依赖清单
   pip install -r requirements.txt
   ```
2. 启动 Hy3 服务（以 vLLM 为例）：
   ```bash
   vllm serve tencent/Hy3 --tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice --served-model-name hy3
   ```
   启动后 `base_url` 默认为 `http://127.0.0.1:8000/v1`，`api_key` 用占位符 `EMPTY`。
3. 确认服务可达：
   ```bash
   curl http://127.0.0.1:8000/v1/models
   ```

> SGLang 用户把启动参数换成 `--tool-call-parser hunyuan --reasoning-parser hunyuan` 即可，其余调用方式完全一致。（`--reasoning-parser` 用于解析思考过程 reasoning_content，仅思考模式需要）

## 2. 设置环境变量

```bash
export HY3_BASE_URL='http://127.0.0.1:8000/v1'
export HY3_API_KEY='EMPTY'
export HY3_MODEL='hy3'
```

模型名默认 `hy3`，需与服务启动时的 `--served-model-name` 一致（以 `GET /v1/models` 为准）。

## 3. 用 curl 完成第一次调用

```bash
curl "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "用一句话解释什么是 API。"}],
    "max_tokens": 256,
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

成功后回答位于 `choices[0].message.content`，`finish_reason` 表示结束原因，`usage` 记录 token 用量。

**典型响应：**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "hy3",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "API（应用程序编程接口）是不同软件组件之间进行交互的约定和工具..."},
    "finish_reason": "stop"
  }],
  "usage": {"prompt_tokens": 16, "completion_tokens": 42, "total_tokens": 58}
}
```

## 4. 用 Python OpenAI SDK 调用

最小示例：
```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=60,
)
response = client.chat.completions.create(
    model=os.environ.get("HY3_MODEL", "hy3"),
    messages=[{"role": "user", "content": "用一句话解释什么是 API。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print(response.choices[0].message.content)
```

运行仓库完整示例：
```bash
pip install -r requirements.txt
python 01_basic_chat.py
```

## 5. 参数说明

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `model` | string | `"hy3"` | 需与服务端 `--served-model-name` 一致 |
| `messages` | array | *必填* | 对话历史，角色：`system` / `user` / `assistant` / `tool` |
| `temperature` | number | — | `[0, 2]`，越高越随机。通用 `0.9`，确定性任务 `0.3` |
| `top_p` | number | — | `[0, 1]` 核采样。通常与 `temperature` 二选一 |
| `max_tokens` | integer | — | 最大生成 token（思考与答案共享额度），复杂思考需调大 |
| `stop` | string/array | — | 最多 4 个停止序列，如 `"stop": ["\n\n"]` |
| `stream` | boolean | `false` | `true` 时逐 chunk 返回，降低感知延迟 |
| `tools` | array | — | OpenAI Function Calling 工具定义；**模型只提出调用，应用侧执行** |
| `tool_choice` | string/object | `"auto"` | `"auto"` / `"none"` / `"required"` / 指定函数 |
| `parallel_tool_calls` | boolean | `true` | 每次只处理一个工具调用时设 `false` |
| `chat_template_kwargs.reasoning_effort` | string | `"no_think"` | 思考模式开关（见下节） |

## 6. 思考模式（Reasoning Mode）

开启后响应含额外 `reasoning_content` 字段（模型内部推理，**不应直接展示给用户**）。

```python
# 关闭思考（默认，最快）
extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
# 深度思考
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}
```

| 取值 | 适用场景 |
| --- | --- |
| `no_think` | 简单问答、翻译、格式转换 → 最快 |
| `low` | 一般推理任务 → 平衡速度与质量 |
| `high` | 数学证明、复杂代码、多步规划 → 最深思考 |

> 开启思考模式需要服务端在启动时启用 reasoning parser（vLLM: `--reasoning-parser hy_v3`；SGLang: `--reasoning-parser hunyuan`），否则 `reasoning_content` 不会被解析出来（见第 9 节排查表）。
>
> 多轮工具循环**且开启思考时**，建议把 `reasoning_content` 原样保留在 assistant 消息里（与 `content`、`tool_calls` 同级），以免后续轮次丢失上下文。

完整对比见 [`05_reasoning_mode.py`](05_reasoning_mode.py) 与 [`05_reasoning_mode.md`](05_reasoning_mode.md)。

## 7. 工具调用（Tool Calling）

**服务端前置**：启动 vLLM 时加 `--tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice`；SGLang 加 `--tool-call-parser hunyuan --reasoning-parser hunyuan`。（`--reasoning-parser` 仅思考模式需要，纯工具调用可省略）

**应用侧流程**：
1. 定义 `tools`（JSON Schema）
2. 发送 `messages` + `tools`，`tool_choice="auto"`
3. 读 `response.choices[0].message.tool_calls`
4. **本地执行**对应函数
5. 结果以 `role="tool"` 追加回 `messages`
6. 再调用模型拿最终回答；循环至无 `tool_calls`

完整多轮循环见 [`04_tool_calling.py`](04_tool_calling.py) 与 [`04_tool_calling.md`](04_tool_calling.md)。

## 8. 速率限制与重试

本地部署的速率主要取决于你的 GPU 显存与并发设置，没有云端 QPM / TPM 配额。

| 状态码 | 重试？ | 处理 |
| --- | --- | --- |
| 400 / 401 / 403 | ❌ 立即修正 | 检查格式 / Key / 权限 |
| 429 | ✅ 有限重试 | 降低并发 + 指数退避 |
| 502 / 503 / 504 | ✅ 有限重试 | 服务临时不可用 |
| 连接失败 / 超时 | ✅ 有限重试 | 检查服务是否存活、端口是否正确 |

**重试策略**：指数退避 + jitter，并设总等待预算上限。完整实现见 [`06_error_handling_retry.py`](06_error_handling_retry.py) 与 [`06_error_handling_retry.md`](06_error_handling_retry.md)。

## 9. 常见错误排查

| 现象 | 可能原因 | 解决 |
| --- | --- | --- |
| **401** | Key 缺失 / 错误 | 确认 `HY3_API_KEY`（本地部署用 `EMPTY`） |
| **400** | 请求格式错误 | 检查 `messages` / `tools` 结构 |
| **429** | 并发过高 | 降低并发、加退避 |
| **连接拒绝** | URL 错误 / 服务未起 | 检查 `/v1` 路径、确认服务在 `127.0.0.1:8000` 监听 |
| **finish_reason=length** | 达 `max_tokens` | 调大 `max_tokens` |
| **tool_calls 空** | parser 未启用 | 启动加 `--tool-call-parser` |
| **缺 reasoning_content** | 未开思考 / 未启用 reasoning parser | 设置 `reasoning_effort`，且服务端启动加 `--reasoning-parser hy_v3`（vLLM）/ `--reasoning-parser hunyuan`（SGLang） |

## 10. 示例索引

所有示例位于**当前目录**，每个都是**自包含单文件**，直接调 OpenAI SDK，无共享依赖，并配有同名 `.md` 文档（含完整请求 / 响应解析 / 示例输出）。

| # | 主题 | 脚本 | 文档 |
| --- | --- | --- | --- |
| 01 | [基础对话](01_basic_chat.md) | [`01_basic_chat.py`](01_basic_chat.py) | 单轮 & 多轮 |
| 02 | [流式输出](02_streaming.md) | [`02_streaming.py`](02_streaming.py) | 逐 chunk 解析 |
| 03 | [时延对比](03_latency_compare.md) | [`03_latency_compare.py`](03_latency_compare.py) | TTFT / 总耗时 |
| 04 | [工具调用](04_tool_calling.md) | [`04_tool_calling.py`](04_tool_calling.py) | 单调用 & 多轮循环 |
| 05 | [思考模式](05_reasoning_mode.md) | [`05_reasoning_mode.py`](05_reasoning_mode.py) | no_think / high 对比 |
| 06 | [错误重试](06_error_handling_retry.md) | [`06_error_handling_retry.py`](06_error_handling_retry.py) | 退避 & jitter |

**推荐学习顺序：** `01 → 02 → 03 → 04 → 05 → 06`，按编号顺序逐个运行。

---

## 参考文档
- [官方 README](https://github.com/Tencent-Hunyuan/Hy3)（部署 / vLLM / SGLang）
