# Hy3 API Quickstart

这份文档面向第一次接入 Hy3 的开发者，目标是让你在几分钟内完成一次可运行的 API 调用，并知道常见参数和排障方法。

## 1. 基础信息

Hy3 暴露的是 OpenAI-compatible Chat Completions 接口。按照当前仓库 README 的示例，最常见的本地部署参数如下：

| 项目 | 值 | 说明 |
| --- | --- | --- |
| `base_url` | `http://127.0.0.1:8000/v1` | OpenAI 兼容接口根路径 |
| `api_key` | `EMPTY` | 本地未鉴权服务可直接写 `EMPTY`；如果你启用了鉴权，请改成真实 key |
| `model` | `hy3` | README 示例里的服务名 |
| 主要接口 | `POST /chat/completions` | 与 OpenAI Chat Completions 兼容 |

推荐先完成服务部署，再调用 API：

- vLLM：参考仓库 README 中的 vLLM 部署章节
- SGLang：参考仓库 README 中的 SGLang 部署章节

### 速率限制说明

当前仓库没有定义一个固定的官方 QPS / RPM / TPM 限额。对大多数自部署场景来说，吞吐和并发能力主要取决于：

- 你的推理框架配置，例如 vLLM 或 SGLang
- GPU 数量、显存和 batch/concurrency 配置
- 是否开启流式输出、工具调用、长上下文或高推理强度

如果服务繁忙，常见表现是：

- 返回 `429 Too Many Requests`
- 返回 `503` / `504`
- 首 token 延迟明显升高
- 流式连接中途断开

建议客户端默认实现：

- 请求超时
- 指数退避重试
- 并发控制
- 流式解析失败后的兜底日志

## 2. 最小可运行示例

### curl

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "介绍一下 Hy3"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512,
    "chat_template_kwargs": {
      "reasoning_effort": "no_think"
    }
  }'
```

说明：

- `extra_body` 是 OpenAI Python SDK 的辅助参数，用来把额外字段展开到最终请求体里
- 如果你直接发 HTTP JSON，请把 `chat_template_kwargs` 作为顶层字段传递，不要再包一层 `extra_body`

成功响应通常会包含：

- `choices[0].message.content`：模型最终回答
- `usage`：token 统计，是否返回取决于服务端实现
- `id` / `created` / `model`：请求元数据

### Python OpenAI SDK

先安装依赖：

```bash
pip install openai
```

最小示例：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "介绍一下 Hy3"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
    extra_body={
        "chat_template_kwargs": {
            "reasoning_effort": "no_think",
        }
    },
)

print(response.choices[0].message.content)
```

## 3. 参数说明

下面列出接入时最常用的参数。

### `temperature`

- 控制采样随机性
- 值越高，输出通常越发散、越有创造性
- 值越低，输出通常越稳定、越保守
- README 当前推荐值：`0.9`

适用建议：

- 日常问答、创作：`0.7` 到 `1.0`
- 代码、结构化输出：`0.1` 到 `0.7`

### `top_p`

- 控制 nucleus sampling 的候选范围
- 一般与 `temperature` 配合使用
- README 当前推荐值：`1.0`

常见建议：

- 如果你已经调 `temperature`，通常保持 `top_p=1.0` 即可
- 需要更保守时可尝试 `0.8` 到 `0.95`

### `max_tokens`

- 控制单次响应最多生成多少输出 token
- 值太小会导致回答被截断
- 值太大则可能增加延迟和显存压力

常见建议：

- 普通问答：`256` 到 `1024`
- 长代码或长推理：按任务逐步调高

### `stop`

- 指定提前停止生成的终止序列
- 可以是一个字符串，也可以是字符串数组

示例：

```json
{
  "stop": ["\nObservation:", "</tool_output>"]
}
```

注意：

- 如果你在做 JSON 输出或工具调用，不要把 `stop` 设成可能截断结构化内容的字符串
- 流式场景下，`stop` 触发后客户端会看到生成自然结束

### `tools`

- 用于把函数工具描述传给模型
- 模型会决定是否发起 `tool_calls`
- 你需要在客户端执行工具，再把工具结果追加回 `messages`

适合场景：

- 天气、搜索、数据库查询、计算器、业务函数调用

如果你用的是 vLLM / SGLang，请确认服务端部署时开启了仓库 README 提到的工具调用相关配置，否则模型可能不会按预期返回工具调用结构。

### 思考模式开关：`reasoning_effort`

Hy3 README 当前给出的可选值是：

- `"no_think"`：直接回复，适合日常对话和低延迟场景
- `"low"`：较轻量推理
- `"high"`：更适合复杂数学、代码和推理任务

设置方式：

```python
extra_body={
    "chat_template_kwargs": {
        "reasoning_effort": "high"
    }
}
```

说明：

- 如果服务端不返回可见思考内容，不要假设一定能看到推理过程文本
- 实际上更可靠的比较方式是观察最终答案质量、首 token 延迟和总耗时

## 4. 响应解析

最常见的非流式响应读取方式：

```python
message = response.choices[0].message
print(message.content)
```

流式响应读取方式：

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "请用三句话介绍 Hy3"}],
    stream=True,
)

for chunk in response:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
```

## 5. 常见报错排查

### 1. API key 错误

典型现象：

- `401 Unauthorized`
- SDK 抛出 `AuthenticationError`

排查方法：

- 检查 `api_key` 是否与服务端配置一致
- 本地未鉴权部署时，确认你确实使用了 `EMPTY`
- 检查请求头里是否传了 `Authorization: Bearer ...`

### 2. 模型名错误

典型现象：

- `404` 或 `400`
- 错误信息里出现 `model not found`

排查方法：

- 检查 `model="hy3"` 是否与你的 `--served-model-name` 一致
- 如果部署时改过服务名，客户端也要同步修改

### 3. 网络超时

典型现象：

- 连接超时
- 读取超时
- SDK 抛出 `APIConnectionError` 或 `APITimeoutError`

排查方法：

- 确认服务已启动，并监听在正确端口
- 检查 `base_url` 是否正确，尤其是 `/v1`
- 长回答、慢思考、高并发场景下适当调大 timeout
- 对网络层错误做重试

### 4. 限流或服务繁忙

典型现象：

- `429 Too Many Requests`
- `503`、`504`

排查方法：

- 降低并发
- 减小 `max_tokens`
- 对 `429` 和部分 `5xx` 做指数退避重试
- 观察服务端日志和 GPU 利用率

### 5. 流式解析错误

典型现象：

- SSE / chunk 被中断
- 客户端只打印出部分文本
- JSON 解析失败或前端事件流断开

排查方法：

- 逐 chunk 判断 `delta.content` 是否为空，不要假设每个 chunk 都有文本
- 兼容最后一个结束 chunk
- 网络不稳定时记录已收到内容，便于断点排查
- 如果你自己封装了前端流式代理，确认没有把 chunk 拼接坏

### 6. 参数错误

典型现象：

- `400 Bad Request`

排查方法：

- 打印实际请求参数
- 检查 `messages` 格式是否正确
- 检查 `tools` JSON Schema 是否合法
- 检查 `reasoning_effort` 是否为 `no_think`、`low`、`high`

## 6. 推荐阅读示例

仓库中还提供了 6 个完整示例：

- [../examples/01_basic_chat.py](../examples/01_basic_chat.py)
- [../examples/02_streaming.py](../examples/02_streaming.py)
- [../examples/03_streaming_vs_non_streaming.py](../examples/03_streaming_vs_non_streaming.py)
- [../examples/04_tool_calling.py](../examples/04_tool_calling.py)
- [../examples/05_reasoning_mode.py](../examples/05_reasoning_mode.py)
- [../examples/06_error_handling_retry.py](../examples/06_error_handling_retry.py)

建议顺序：

1. 先跑 `01_basic_chat.py`
2. 再看 `02_streaming.py` 和 `03_streaming_vs_non_streaming.py`
3. 需要 Agent / 函数调用时看 `04_tool_calling.py`
4. 需要复杂推理调优时看 `05_reasoning_mode.py`
5. 上生产前看 `06_error_handling_retry.py`
