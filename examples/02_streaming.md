# 示例 02：流式输出（逐 chunk 解析）

> 对应脚本：[`02_streaming.py`](02_streaming.py)

非流式模式下要等模型把整段回答生成完才一次性返回；流式模式边生成边返回，显著降低“感知延迟”，适合做打字机效果或实时 UI。

## 完整请求

```python
stream = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "用三句话介绍腾讯混元大模型。"}],
    temperature=0.9,
    max_tokens=256,
    stream=True,                            # 开启流式
    stream_options={"include_usage": True},# 让最后一个 chunk 带上 usage
    extra_body=REASONING,
)
```

curl 等价写法（加 `"stream": true`）：

```bash
curl "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "用三句话介绍腾讯混元大模型。"}],
    "max_tokens": 256,
    "stream": true,
    "stream_options": {"include_usage": true},
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

## 完整响应解析

`create(stream=True)` 返回的是一个**生成器（stream）**，不是完整响应。用 `for chunk in stream:` 逐个取出 `ChatCompletionChunk`：

```json
{"choices":[{"delta":{"content":"腾讯"},"finish_reason":null}],"usage":null}
{"choices":[{"delta":{"content":"混元"},"finish_reason":null}],"usage":null}
{"choices":[{"delta":{"content":""},"finish_reason":"stop"}],"usage":null}
{"choices":[],"usage":{"prompt_tokens":18,"completion_tokens":45,"total_tokens":63}}
```

| 字段 | 含义 |
|---|---|
| `choices[0].delta.content` | 这一小片**新生成**的文字（流式中 `message` 换成 `delta`） |
| `choices[0].finish_reason` | 仅最后一个内容 chunk 有值，`stop`/`length` |
| `usage` | 仅最后一个**独立尾块**有值（需 `stream_options={"include_usage": true}`）；该尾块 `choices` 为空列表，循环里要先判断 `if not chunk.choices` 再取 `delta` |

> 首包往往只带 `role`、不带 `content`，所以代码里用 `if delta.content:` 判断是否有文字再打印。

## 逐 chunk 解析循环

```python
full_text = ""
for chunk in stream:
    if not chunk.choices:                           # usage 尾块：空 choices，仅带 usage
        if chunk.usage is not None:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens
            total_tokens = chunk.usage.total_tokens
        continue
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)   
        full_text += delta.content
    if chunk.usage is not None:                     
        prompt_tokens = chunk.usage.prompt_tokens
        completion_tokens = chunk.usage.completion_tokens
        total_tokens = chunk.usage.total_tokens
    if chunk.choices[0].finish_reason:              # 最后一个内容块
        print(f"\n\n[finish_reason={chunk.choices[0].finish_reason}]")
```

## 示例输出

```
=== 流式输出（逐字打印） ===

腾讯混元大模型是腾讯自主研发的通用大语言模型，具备强大的中文理解、逻辑推理与多模态生成能力。它支持对话交互、内容创作、代码编写等多种任务，并深度集成于腾讯云及微信等产品中。混元持续迭代升级，致力于为企业与开发者提供安全、可靠、高效的AI基础设施服务。

[finish_reason=stop]

--- 拼接后的完整回答 ---
腾讯混元大模型是腾讯自主研发的通用大语言模型，具备强大的中文理解、逻辑推理与多模态生成能力。它支持对话交互、内容创作、代码编写等多种任务，并深度集成于腾讯云及微信等产品中。混元持续迭代升级，致力于为企业与开发者提供安全、可靠、高效的AI基础设施服务。
Token 用量：prompt=24, completion=70, total=94
```
