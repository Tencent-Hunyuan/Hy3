# Hy3 API Quickstart

> 目标：5 分钟完成第一次调用，半小时上手主要能力。  
> 本文面向 **腾讯云 TokenHub 托管 API**（OpenAI 兼容）。本地 vLLM / SGLang 部署请看仓库 [README](./README_CN.md)；两者参数不完全相同，请勿混用。

## 1. 基础信息


| 项                  | 值                                          |
| ------------------ | ------------------------------------------ |
| Base URL（国内 / 广州）  | `https://tokenhub.tencentmaas.com/v1`      |
| Base URL（国际 / 新加坡） | `https://tokenhub-intl.tencentmaas.com/v1` |
| Chat Completions   | `{BASE_URL}/chat/completions`              |
| Model              | `hy3`（可选 `hy3-preview`）                    |
| Auth               | `Authorization: Bearer <API_KEY>`          |
| 推荐采样               | `temperature=0.9`，`top_p=1.0`              |
| 上下文                | 256K（最大输入约 192K，最大输出约 128K）                |


### 获取 API Key

1. 打开 [TokenHub API Key 管理](https://cloud.tencent.com/document/product/1823/130090) 按文档创建 Key。
2. 仅通过环境变量注入，不要写进代码、截图或提交到 Git。

```bash
export HY3_API_KEY='your-api-key'
export HY3_BASE_URL='https://tokenhub.tencentmaas.com/v1'
export HY3_MODEL='hy3'
```



### 速率限制

QPM / RPM、TPM、TPD 与并发上限取决于套餐与 Key 配置，以控制台为准。触发限流时常见 HTTP `429`，响应可能带 `Retry-After`（秒）。生产环境应对 429 / 5xx / 超时做有限重试；401 / 403 / 402 等鉴权与额度错误应立刻修正，不要盲目重试。

---



## 2. 最小可运行示例



### 2.1 curl

```bash
curl "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "用一句话介绍你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256
  }'
```

成功时重点看：

- `choices[0].message.content`：最终回答
- `choices[0].finish_reason`：结束原因（如 `stop`）
- `usage`：token 用量



### 2.2 Python（OpenAI SDK）

```bash
pip install openai
```

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["HY3_API_KEY"],
    base_url=os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"),
)

resp = client.chat.completions.create(
    model=os.environ.get("HY3_MODEL", "hy3"),
    messages=[{"role": "user", "content": "用一句话介绍你自己。"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
)
print(resp.choices[0].message.content)
```

更完整的 6 个可运行示例见 [examples/api/](./examples/api/)。

---



## 3. 参数说明


| 参数                      | 说明                                                                                     |
| ----------------------- | -------------------------------------------------------------------------------------- |
| `temperature`           | `[0, 2]`，越高越随机。通常与 `top_p` 二选一细调。                                                      |
| `top_p`                 | `[0, 1]` 核采样阈值。官方推荐日常对话 `1.0`。                                                         |
| `max_tokens`            | 生成上限；**思考 token 与最终答案共享额度**。开启深度思考时建议显著加大（如 ≥ 16000）。                                  |
| `stop`                  | 停止串（string 或最多 4 个 string）；命中后停止，响应不含停止串本身。                                            |
| `stream`                | `true` 时 SSE 流式返回；可配 `stream_options={"include_usage": true}` 在末尾拿到 usage。             |
| `tools` / `tool_choice` | OpenAI Function Calling。模型只提出 `tool_calls`，业务侧执行后以 `role=tool` 回填。                     |
| `thinking`              | 托管 API 顶层字段：`{"type":"enabled"}` / `{"type":"disabled"}`。Python SDK 用 `extra_body` 传入。 |
| `reasoning_effort`      | 思考强度：`low` / `medium` / `high`（以及本地部署文档中的 `no_think`）。托管侧同样经 `extra_body` 透传。          |




### 思考模式开关（托管 API）

```python
# 开启思考，并从响应读取 reasoning_content
resp = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "小明有 5 个苹果，给了小红 2 个，又买了 3 个，还剩几个？"}],
    extra_body={
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
    },
)
msg = resp.choices[0].message
print("思考:", getattr(msg, "reasoning_content", None))
print("回答:", msg.content)
```

> **注意**：仓库 README 里本地部署示例使用  
> `extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}`。  
> 这是 vLLM / SGLang 路径；**TokenHub 托管请用顶层** `thinking` **/** `reasoning_effort`。



### 工具调用要点

1. 请求带 `tools`，模型可能返回 `finish_reason=tool_calls`。
2. 将 assistant 消息（含 `content`、`tool_calls`，以及若有的 `reasoning_content`）原样追加到 `messages`。
3. 业务执行工具后追加 `{"role":"tool","tool_call_id": "...","content": "..."}`。
4. 再次请求，直到得到最终文本答案。

带 tools 时，若设置 `reasoning_effort=low`，官方说明 API 可能自动映射为 `high`（兼容自适应思考）。

---



## 4. 常见报错排查


| 现象                     | 可能原因                    | 处理                                          |
| ---------------------- | ----------------------- | ------------------------------------------- |
| `401`                  | Key 缺失 / 错误 / 过期        | 检查 `HY3_API_KEY` 是否在当前 shell 生效             |
| `403`                  | 无模型权限、账号受限、IP 白名单       | 控制台核对模型授权与账号状态                              |
| `400` / 参数错误           | model 名错误、messages 格式非法 | 确认 `hy3`，messages 以 `user` 结尾               |
| `429`                  | 限流                      | 降并发，遵守 `Retry-After`，指数退避                   |
| `502` / `503` / `504`  | 上游临时故障                  | 有限重试；长期失败查服务状态                              |
| 连接失败 / DNS             | Base URL 地域或路径错误        | 确认是否带 `/v1`，国内外入口是否一致                       |
| 空回答 / 截断               | `max_tokens` 过小         | 思考模式加大 `max_tokens`                         |
| `finish_reason=length` | 触及生成上限                  | 增大 `max_tokens` 或缩短任务                       |
| SDK 读不到思考字段            | 字段非标                    | 用 `getattr(msg, "reasoning_content", None)` |


完整错误码见 [TokenHub API 错误码](https://cloud.tencent.com/document/product/1823/131595)。

---



## 5. 下一步


| 示例                                                       | 说明               |
| -------------------------------------------------------- | ---------------- |
| [01_basic_chat](./examples/api/01_basic_chat/)           | 单轮 / 多轮对话        |
| [02_streaming](./examples/api/02_streaming/)             | 流式请求与 chunk 解析   |
| [03_latency_compare](./examples/api/03_latency_compare/) | 非流式 vs 流式时延      |
| [04_tool_calling](./examples/api/04_tool_calling/)       | 单次工具调用 + 多轮工具循环  |
| [05_reasoning_mode](./examples/api/05_reasoning_mode/)   | 思考开 / 关对比        |
| [06_error_handling](./examples/api/06_error_handling/)   | 超时 / 限流 / 网络错误重试 |


```bash
cd examples/api
pip install -r requirements.txt
cp .env.example .env   # 填入 HY3_API_KEY
python 01_basic_chat/main.py
```

六个示例已于 **2026-07-18** 在 TokenHub 广州入口使用 `model=hy3` 实测通过；各目录 README 中的示例输出为脱敏后的实测结果。

## 参考

- [TokenHub 混元调用指南（含 Hy3）](https://cloud.tencent.com/document/product/1823/132252)
- [TokenHub API 使用说明](https://cloud.tencent.com/document/product/1823/130078)
- [深度思考](https://cloud.tencent.com/document/product/1823/131208)
- [API 错误码](https://cloud.tencent.com/document/product/1823/131595)

