# Hy3 托管 API：5 分钟快速开始

第一次接入时，按第 1～4 节操作即可。后面的参数、重试和错误排查可以等首次调用
成功后再看。本文只介绍腾讯云托管 API；仓库 README 中 vLLM/SGLang 的
`chat_template_kwargs` 是本地部署参数，不能用于 TokenHub。

## 1. 准备 Key 和接口地址

先在 TokenHub 或 Token Plan 控制台开通 Hy3 并创建 API Key。国内站通常使用广州
入口；如果开通的是新加坡站或 Token Plan，请改用对应地址。Key 和接口地址必须
属于同一产品和地域。

| 产品/地域 | `HY3_BASE_URL` |
|---|---|
| TokenHub 广州 | `https://tokenhub.tencentmaas.com/v1` |
| TokenHub 新加坡 | `https://tokenhub-intl.tencentmaas.com/v1` |
| Token Plan 个人版 | `https://api.lkeap.cloud.tencent.com/plan/v3` |

默认服务 ID 是 `hy3`。自定义在线推理服务可能使用 `ep-xxxxxxxx`，请以控制台或
`GET /v1/models` 的结果为准。

## 2. 在本机设置环境变量

不要把 API Key 写入代码、`.env.example`、命令历史截图、日志或聊天。下面的值只
在当前终端生效。

PowerShell：

```powershell
$env:HY3_API_KEY = "从控制台复制的 Key"
$env:HY3_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
$env:HY3_MODEL = "hy3"
```

Bash：

```bash
export HY3_API_KEY='从控制台复制的 Key'
export HY3_BASE_URL='https://tokenhub.tencentmaas.com/v1'
export HY3_MODEL='hy3'
```

## 3. 用 curl 完成第一次调用

PowerShell：

```powershell
curl.exe "$env:HY3_BASE_URL/chat/completions" `
  -H "Authorization: Bearer $env:HY3_API_KEY" `
  -H "Content-Type: application/json" `
  -d '{"model":"hy3","messages":[{"role":"user","content":"用一句话介绍 Hy3。"}],"max_tokens":256,"thinking":{"type":"disabled"}}'
```

Bash：

```bash
curl "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "用一句话介绍 Hy3。"}],
    "max_tokens": 256,
    "thinking": {"type": "disabled"}
  }'
```

成功后，回答在 `choices[0].message.content` 中；`finish_reason` 表示结束原因，
`usage` 记录 token 用量。如果请求失败，直接跳到下方的“常见错误”。不要把 `id`
当成业务数据或收录进公开示例输出。

## 4. 用 OpenAI Python SDK 调用

从仓库根目录执行：

```powershell
python -m pip install -r examples/api/requirements.txt
python examples/api/01_basic_chat.py
```

最小 SDK 请求等价于：

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["HY3_API_KEY"],
    base_url=os.environ["HY3_BASE_URL"],
)
response = client.chat.completions.create(
    model=os.getenv("HY3_MODEL", "hy3"),
    messages=[{"role": "user", "content": "用一句话介绍 Hy3。"}],
    max_tokens=256,
    extra_body={"thinking": {"type": "disabled"}},
)
print(response.choices[0].message.content)
```

## 5. 常用参数

| 参数 | Hosted API 用法 |
|---|---|
| `temperature` | `[0, 2]`；越高越随机。通常与 `top_p` 二选一调节。 |
| `top_p` | `[0, 1]` 的核采样阈值。 |
| `max_tokens` | 推理 token 与最终答案共享额度；复杂思考任务需要显著调大。 |
| `stop` | 字符串或最多 4 个字符串；命中后停止且不返回停止串。 |
| `tools` | OpenAI Function Calling 工具数组；模型只提出调用，业务代码负责执行。 |
| `stream` | `true` 时逐 chunk 返回；配合 `stream_options={"include_usage": true}` 获取 usage 尾块。 |
| `thinking` | 顶层 `{"type":"enabled"}` 或 `{"type":"disabled"}`。Hy3 默认关闭。 |
| `reasoning_effort` | 开启思考后使用 `low`、`medium`、`high`。Hy3 文档默认 `low`。 |

Python SDK 尚未把所有 TokenHub 扩展字段声明为显式参数，因此把 `thinking` 和
`reasoning_effort` 放入 `extra_body`。工具循环中必须把模型返回的
`reasoning_content` 原样放回它所属的 assistant 消息，并与 `content`、
`tool_calls` 同级。

## 速率限制与重试

QPM/RPM、TPM、TPD 和并发限制取决于模型、套餐与 API Key 配置，不存在一个适合
所有用户的固定数字。以控制台显示为准。HTTP 429 可能包含整数或字符串业务码，
并通过 `Retry-After` 给出等待秒数。

- 400、401、402、403 等请求、鉴权、额度或权限错误应立即修正，不自动重试。
- 429、502、503、504、连接错误和超时可有限重试。
- 优先遵守 `Retry-After`；否则使用有限指数退避和 jitter。
- 达到最大尝试次数或总等待预算后停止；额度耗尽不能靠无限重试解决。

## 常见错误

| 现象 | 排查 |
|---|---|
| 401 | Key 缺失、错误、过期或禁用；确认当前终端的环境变量。 |
| 400004 / 401006 | `HY3_MODEL` 或服务 ID 错误/不匹配；查看控制台或 `/v1/models`。 |
| 403 | Key 无模型权限、IP 不在白名单、账号或工具不可用。 |
| 429 | 降低并发和 token 速率，遵守 `Retry-After`，再检查控制台配额。 |
| 429006 | 上游模型服务繁忙或达到容量上限；做有限退避后再试。 |
| 502/503/504 | 上游临时失败；按有限重试策略处理。 |
| 连接失败 | 检查 Base URL 地域、`/v1` 或 `/plan/v3` 路径、代理和 DNS。 |
| `finish_reason=length` | 增大 `max_tokens` 或缩短任务；思考与答案共享额度。 |

## 继续学习

第一次接入建议先运行基础对话和流式输出。工具调用、思考模式、时延测量和重试可以
按需学习，入口见 [examples/api/README.md](examples/api/README.md)。

## 验证说明

本文和六个示例已于 2026-07-17 在 TokenHub 广州入口使用 `model=hy3` 实测通过。
示例只保留脱敏后的输出、参数和测量样本，不包含凭据、HTTP headers、
response/request ID 或账户信息。模型文本、chunk 切分、时延和 jitter 每次运行都
可能不同。

参考文档：

- [TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078)
- [语言模型调用概览](https://cloud.tencent.com/document/product/1823/130079)
- [深度思考](https://cloud.tencent.com/document/product/1823/131208)
- [保留式思考模式](https://cloud.tencent.com/document/product/1823/133534)
- [API 错误码](https://cloud.tencent.com/document/product/1823/131595)
- [Token Plan 个人版](https://cloud.tencent.com/document/product/1823/130060/)
