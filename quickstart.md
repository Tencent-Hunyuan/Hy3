# Hy3 API Quickstart

本指南面向希望直接调用 Hy3 托管 API 的开发者。完成“5 分钟快速调用”后，可继续运行 `examples/api/` 中的 6 个示例，在约半小时内了解多轮对话、流式输出、工具调用、思考模式和错误重试。

> 本文默认使用腾讯云 TokenHub 的 OpenAI 兼容接口。自托管 vLLM/SGLang 的调用差异见[自托管服务](#自托管服务)。

## 5 分钟快速调用

### 1. 准备 API Key

1. 登录 [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub)。
2. 开通 Hy3 在线推理服务。
3. 在 [API Key 管理](https://console.cloud.tencent.com/tokenhub/apikey)中创建 Key，并确保它有权访问 Hy3。

API Key 只会以环境变量读取。不要把真实 Key 写入代码、文档、Notebook 或 Git 提交。

### 2. 设置环境变量

广州地域：

```bash
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
export HY3_MODEL="hy3"
read -s HY3_API_KEY && export HY3_API_KEY
```

新加坡地域请使用：

```bash
export HY3_BASE_URL="https://tokenhub-intl.tencentmaas.com/v1"
```

TokenHub 不支持跨地域、跨站点调用，请使用服务开通地域对应的地址。

### 3. 使用 curl 调用

```bash
curl --fail-with-body --silent --show-error \
  "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "请用一句话介绍 Hy3。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "thinking": {"type": "disabled"}
  }'
```

响应结构示例：

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hy3 是腾讯混元团队研发的快慢思考融合混合专家模型。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 19,
    "completion_tokens": 25,
    "total_tokens": 44
  }
}
```

响应文本不是固定值；上面的 ID 和 Token 数仅用于展示字段结构。

### 4. 使用 Python OpenAI SDK 调用

建议使用 Python 3.10 或更高版本：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r examples/api/requirements.txt
```

新建 `hello_hy3.py`：

```python
import os

from openai import OpenAI

api_key = os.environ.get("HY3_API_KEY")
if not api_key:
    raise SystemExit("请先设置 HY3_API_KEY")

client = OpenAI(
    api_key=api_key,
    base_url=os.environ.get(
        "HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"
    ),
    timeout=60.0,
)

response = client.chat.completions.create(
    model=os.environ.get("HY3_MODEL", "hy3"),
    messages=[{"role": "user", "content": "请用一句话介绍 Hy3。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"thinking": {"type": "disabled"}},
)

choice = response.choices[0]
print(choice.message.content)
print("finish_reason:", choice.finish_reason)
if response.usage:
    print("usage:", response.usage.model_dump())
```

运行：

```bash
python hello_hy3.py
```

## API 基础信息

| 配置 | 广州 | 新加坡 |
| --- | --- | --- |
| SDK `base_url` | `https://tokenhub.tencentmaas.com/v1` | `https://tokenhub-intl.tencentmaas.com/v1` |
| Chat Completions URL | `https://tokenhub.tencentmaas.com/v1/chat/completions` | `https://tokenhub-intl.tencentmaas.com/v1/chat/completions` |
| 鉴权 | `Authorization: Bearer <API_KEY>` | 同左 |
| `model` | `hy3` | `hy3` |

也可以调用 `GET /v1/models` 查询当前 Key 可访问且在线的模型：

```bash
curl --fail-with-body --silent --show-error \
  "$HY3_BASE_URL/models" \
  -H "Authorization: Bearer $HY3_API_KEY"
```

## 常用参数

| 参数 | 类型 | 作用与建议 |
| --- | --- | --- |
| `temperature` | float | 采样温度，范围 `[0, 2]`。越高越随机。 |
| `top_p` | float | 核采样阈值，范围 `[0, 1]`。通常与 `temperature` 二选一调节。 |
| `max_tokens` | int | 最大输出 Token 数；思考 Token 与回答 Token 共享额度，思考模式下应适当调大。 |
| `stop` | string 或 string[] | 命中任一停止序列时停止，停止序列不会出现在响应中。 |
| `stream` | bool | `true` 时返回流式 chunk。 |
| `stream_options` | object | 流式时使用 `{"include_usage": true}` 可在尾包取得用量。 |
| `tools` | array | Function Calling 工具定义，包含函数名称、描述和 JSON Schema 参数。 |
| `tool_choice` | string/object | `none`、`auto`、`required`，或强制调用指定函数。 |
| `parallel_tool_calls` | bool | 是否允许一次响应请求多个工具，默认 `true`。 |
| `thinking` | object | `{"type":"enabled"}` 开启，`{"type":"disabled"}` 关闭。Hy3 默认关闭。 |
| `reasoning_effort` | string | 思考强度：`low`、`medium`、`high`；仅在开启思考时有意义。 |

推荐从 `temperature=0.9`、`top_p=1.0` 开始。需要结果更稳定时降低 `temperature`；不要同时大幅调整两个采样参数。

### Python 中传递思考参数

`thinking` 和 `reasoning_effort` 是 TokenHub 扩展字段，通过 OpenAI SDK 的 `extra_body` 传入：

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "证明根号 2 是无理数。"}],
    max_tokens=2048,
    extra_body={
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    },
)

message = response.choices[0].message
reasoning = getattr(message, "reasoning_content", None)
print("reasoning:", reasoning)
print("answer:", message.content)
```

工具调用与思考模式组合使用时，应把 assistant 消息中的 `reasoning_content` 与 `tool_calls` 一起原样放回后续请求历史。

## 速率限制与配额

TokenHub 的具体限额取决于账户、模型服务和购买/体验配额，没有适用于所有账户的单一固定数字。请在控制台的在线推理服务详情中查看当前 RPM（每分钟请求数）、TPM（每分钟 Token 数）和并发限制。

服务可能按 RPM、TPM、TPD（日 Token 数）或并发数返回 HTTP 429。客户端应：

1. 优先遵守响应头 `Retry-After`；
2. 缺少该响应头时使用带随机抖动的指数退避；
3. 限制最大尝试次数和总等待时间；
4. 持续触发限流时降低并发或申请更高配额。

完整实现见 [`06_error_handling_retry.py`](examples/api/06_error_handling_retry.py)。

## 常见报错排查

| 状态/异常 | 常见原因 | 处理方式 |
| --- | --- | --- |
| 400 | 参数范围错误、消息格式错误 | 检查错误响应中的 `message_zh`；不要原样重试。 |
| 401 | API Key 缺失、错误、过期或无模型权限 | 检查 Bearer Header 和 Key 的访问范围。 |
| 404/模型不可用 | Base URL、路径或 `model` 错误 | 确认 URL 包含 `/v1`，调用 `/models` 检查 `hy3` 状态。 |
| 429 | RPM、TPM、TPD 或并发超限 | 遵守 `Retry-After`，降低请求频率并有限重试。 |
| 451 | 输入或输出触发内容安全策略 | 修改内容；不要对同一请求盲目重试。 |
| 500/502/503/504 | 服务暂时异常或上游不可达 | 使用有限指数退避；持续失败时记录 `request_id` 并提交工单。 |
| `APITimeoutError` | 响应超过客户端超时 | 适当提高 timeout、减小输出长度；注意超时重试可能产生重复计费。 |
| `APIConnectionError` | DNS、代理、证书或网络异常 | 检查网络、代理和地域地址后有限重试。 |
| `finish_reason=length` | 达到 `max_tokens` | 提高输出上限或缩短提示词。 |

排障时保留错误响应中的 `request_id`，但不要公开 API Key 或完整业务输入。

## 半小时上手主要能力

```bash
cd examples/api
cp .env.example .env
# 编辑 .env，填入 HY3_API_KEY

python 01_basic_chat.py
python 02_streaming.py
python 03_latency_comparison.py
python 04_tool_calling.py
python 05_reasoning_mode.py
python 06_error_handling_retry.py
```

示例索引及每个示例的请求、响应解析和示例输出见 [`examples/api/README.md`](examples/api/README.md)。

## 自托管服务

通过本仓库 README 启动 vLLM 或 SGLang 后，可覆盖环境变量：

```bash
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
```

自托管服务没有 TokenHub 账户配额；实际吞吐取决于硬件、并行配置和网关限流。自托管 README 使用 `chat_template_kwargs.reasoning_effort` 控制推理模式，而 TokenHub 使用本文所述的顶层 `thinking` 和 `reasoning_effort`。不要同时发送两套配置。

## 官方参考

- [TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078)
- [语言模型调用概览](https://cloud.tencent.com/document/product/1823/130079)
- [模型列表](https://cloud.tencent.com/document/product/1823/130051)
- [深度思考](https://cloud.tencent.com/document/product/1823/131208)
- [API 错误码说明](https://cloud.tencent.com/document/product/1823/131595)
