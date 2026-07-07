# Non-Streaming vs Streaming Latency

对比普通非流式请求和流式请求的时延。非流式只能得到总耗时；流式可以额外观察首 token 时延。

运行：

```bash
python3 examples/api/latency_compare.py
```

## 完整请求

下面展示本地 vLLM/SGLang 默认请求。使用 OpenRouter、腾讯云或其他远程 provider 时，脚本会根据 `examples/api/common.py` 的配置去掉 Hy3 本地模板参数或合并 `HY3_EXTRA_BODY_JSON`；运行时打印的 request 是实际发送内容。

非流式请求：

```python
{
    "model": "hy3",
    "messages": [
        {
            "role": "user",
            "content": "Write a concise checklist for productionizing a Hy3 API client.",
        }
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

流式请求只额外增加：

```python
{"stream": True}
```

## 完整 response 解析

非流式：

```python
start = time.perf_counter()
response = client.chat.completions.create(**request)
total_s = time.perf_counter() - start

message = response.choices[0].message
print("finish_reason:", response.choices[0].finish_reason)
print("content:", message.content)
print("usage:", response.usage)
```

流式：

```python
start = time.perf_counter()
stream = client.chat.completions.create(**streaming_request)

first_token_s = None
for chunk in stream:
    delta = chunk.choices[0].delta
    content = getattr(delta, "content", None)
    reasoning = getattr(delta, "reasoning_content", None)
    if first_token_s is None and (content or reasoning):
        first_token_s = time.perf_counter() - start

total_s = time.perf_counter() - start
```

## 示例输出

以下输出来自实际调用 OpenRouter `tencent/hy3:free`：

```text
=== non_streaming parsed response ===
finish_reason: length
content: **Productionizing a Hy3 API Client – Checklist**

- [ ] **Authentication**
  - Store credentials/secrets in env vars or secret manager (never hardcode)
  - Implement token refresh / expiry handling
  - Use least-privilege API keys
...
non_streaming_total_s: 4.824

=== latency comparison ===
chunk_count: 136
streaming_first_token_s: 1.814
streaming_total_s: 3.128
non_streaming_total_s: 4.824
streaming_content: **Hy3 API Client Productionization Checklist**

- [ ] **Auth & Secrets**
  - Store API keys/tokens in secrets manager (not code)
  - Support token refresh and rotation
  - Scope permissions to least privilege
...
```

这些数字只适合本机对比。真实时延会受到 GPU 型号、模型预热、队列深度、prompt 长度、生成长度、MTP/speculative decoding 和网络路径影响。
