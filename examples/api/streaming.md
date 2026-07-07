# Streaming

演示 `stream=True` 的流式请求，并逐个解析 chunk 中的 delta 字段。

运行：

```bash
python3 examples/api/streaming.py
```

## 完整请求

下面展示本地 vLLM/SGLang 默认请求。使用 OpenRouter、腾讯云或其他远程 provider 时，脚本会根据 `examples/api/common.py` 的配置去掉 Hy3 本地模板参数或合并 `HY3_EXTRA_BODY_JSON`；运行时打印的 request 是实际发送内容。

```python
{
    "model": "hy3",
    "messages": [
        {
            "role": "user",
            "content": "List four steps for validating a Hy3 API integration.",
        }
    ],
    "temperature": 0.7,
    "top_p": 1.0,
    "max_tokens": 256,
    "stream": True,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think",
        }
    },
}
```

## 完整 response 解析

流式返回不是一次性 `ChatCompletion`，而是多个 chunk。脚本逐 chunk 解析：

```python
for chunk in stream:
    choice = chunk.choices[0]
    delta = choice.delta

    role = getattr(delta, "role", None)
    content = getattr(delta, "content", None)
    reasoning_content = getattr(delta, "reasoning_content", None)
    tool_calls = getattr(delta, "tool_calls", None)
    finish_reason = choice.finish_reason
```

解析策略：

- `delta.role` 通常只在首个 chunk 出现。
- `delta.content` 是增量文本，需要自行拼接。
- `delta.reasoning_content` 只有在服务端暴露 reasoning 字段时出现。
- `delta.tool_calls` 在流式 tool calling 中按片段返回，需要按 tool call id 和 index 合并。
- 最后一个 chunk 通常带有 `finish_reason`。

## 示例输出

以下输出来自实际调用 OpenRouter `tencent/hy3:free`。文档只展示前几个 chunk；脚本运行时会打印完整 chunk 序列。

```text
=== streaming chunks ===
chunk=000 id=gen-1783435271-ezkYYqX8uvxIdy2u4U1G role='assistant' content='Here' reasoning_delta=None reasoning_details=None tool_calls=None finish_reason=None
chunk=001 id=gen-1783435271-ezkYYqX8uvxIdy2u4U1G role='assistant' content=' are four' reasoning_delta=None reasoning_details=None tool_calls=None finish_reason=None
chunk=002 id=gen-1783435271-ezkYYqX8uvxIdy2u4U1G role='assistant' content=' steps for' reasoning_delta=None reasoning_details=None tool_calls=None finish_reason=None
...
chunk=111 id=gen-1783435271-ezkYYqX8uvxIdy2u4U1G role='assistant' content='' reasoning_delta=None reasoning_details=None tool_calls=None finish_reason='stop'

=== final assembled response ===
final_content: Here are four steps for validating a Hy3 API integration:

1. **Authentication & Credential Check**  
   Verify that API keys, tokens, or OAuth credentials are correctly configured and that requests successfully authenticate against the Hy3 endpoint.

2. **Request Schema Validation**  
   Confirm that all required parameters, headers, and payload structures match the Hy3 API specification (e.g., correct JSON format, field names, and data types).

3. **Functional Response Testing**  
   Send test requests for core use cases and verify that the API returns expected status codes, response bodies, and error messages under both success and failure conditions.

4. **End-to-End Integration Verification**  
   Run the integration within your actual application workflow to ensure data flows correctly between Hy3 and your system, including handling rate limits, retries, and webhooks if applicable.
```
