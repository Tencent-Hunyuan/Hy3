# Basic Chat

覆盖单轮对话和多轮对话。脚本会先请求一次 Hy3，再把 assistant 回复加入 `messages`，继续发起第二轮请求。

运行：

```bash
python3 examples/api/basic_chat.py
```

## 完整请求

下面展示本地 vLLM/SGLang 默认请求。使用 OpenRouter、腾讯云或其他远程 provider 时，脚本会根据 `examples/api/common.py` 的配置去掉 Hy3 本地模板参数或合并 `HY3_EXTRA_BODY_JSON`；运行时打印的 request 是实际发送内容。

单轮请求：

```python
{
    "model": "hy3",
    "messages": [
        {
            "role": "user",
            "content": "Introduce Hy3 in one sentence.",
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 128,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think",
        }
    },
}
```

多轮请求会保留上一轮 user 和 assistant：

```python
{
    "model": "hy3",
    "messages": [
        {"role": "user", "content": "Introduce Hy3 in one sentence."},
        {"role": "assistant", "content": "<first response content>"},
        {
            "role": "user",
            "content": "Now give three practical API integration tips.",
        },
    ],
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 256,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think",
        }
    },
}
```

## 完整 response 解析

脚本解析并打印：

```python
choice = response.choices[0]
message = choice.message

print("id:", response.id)
print("model:", response.model)
print("created:", response.created)
print("finish_reason:", choice.finish_reason)
print("role:", message.role)
print("content:", message.content)
print("reasoning_content:", getattr(message, "reasoning_content", None) or getattr(message, "reasoning", None))
print("reasoning_details:", getattr(message, "reasoning_details", None))
print("usage:", response.usage)
```

## 示例输出

以下输出来自实际调用 OpenRouter `tencent/hy3:free`：

```text
=== single_turn parsed response ===
id: gen-1783435257-8O9wEgnzVkApyXfeP0f6
model: tencent/hy3-20260706:free
created: 1783435257
finish_reason: stop
role: assistant
content: Hy3 (Hyperbolic v3) is the latest open-source large language model from Tencent, featuring a 0.5B-parameter lightweight version and supporting hybrid reasoning,agentic capabilities, and efficient deployment.

=== usage ===
{
  "completion_tokens": 44,
  "prompt_tokens": 23,
  "total_tokens": 67
}

=== multi_turn parsed response ===
id: gen-1783435259-ECHjHgjAUcU9UUDYaeRU
model: tencent/hy3-20260706:free
created: 1783435259
finish_reason: stop
role: assistant
content: Here are three practical API integration tips for Hy3:

1. **Use streaming responses for better UX** – Enable Server-Sent Events (SSE) or chunked output when calling Hy3’s chat endpoint so users see tokens incrementally instead of waiting for the full reply, which is especially useful for its hybrid reasoning mode.

2. **Leverage the hybrid reasoning flag** – Explicitly set the `reasoning` parameter (e.g., `light` or `full`) in your API request to control cost and latency; use `light` for simple Q&A and `full` for agentic or complex tasks.

3. **Run the 0.5B model locally for prototyping** – Deploy Hy3-0.5B via the open-source weights or a local server (e.g., with vLLM) to test prompts and agent loops offline before scaling to larger hosted instances, reducing API spend during development.
```
