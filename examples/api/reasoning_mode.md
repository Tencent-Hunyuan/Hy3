# Reasoning Mode

对比 Hy3 的直接回答模式和思考模式。脚本对同一个问题分别发送 `reasoning_effort="no_think"` 与 `reasoning_effort="high"`。

运行：

```bash
python3 examples/api/reasoning_mode.py
```

服务端需要启用 reasoning parser。vLLM 示例：

```bash
--reasoning-parser hy_v3
```

SGLang 示例：

```bash
--reasoning-parser hunyuan
```

## 完整请求

下面展示本地 vLLM/SGLang 默认请求。使用 OpenRouter、腾讯云或其他远程 provider 时，脚本会根据 `examples/api/common.py` 的配置去掉 Hy3 本地模板参数或合并 `HY3_EXTRA_BODY_JSON`；如果远程服务支持 Hy3 reasoning parser，可设置 `HY3_SEND_REASONING=true`。

关闭思考：

```python
{
    "model": "hy3",
    "messages": [
        {
            "role": "user",
            "content": "A service has 3 replicas. Each handles 18 requests per second. Traffic is 41 requests per second. Is there enough capacity?",
        }
    ],
    "temperature": 0.2,
    "top_p": 1.0,
    "max_tokens": 512,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think",
        }
    },
}
```

开启高强度思考时仅替换：

```python
{
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "high",
        }
    }
}
```

## 完整 response 解析

```python
choice = response.choices[0]
message = choice.message
reasoning_content = getattr(message, "reasoning_content", None) or getattr(
    message, "reasoning", None
)
reasoning_details = getattr(message, "reasoning_details", None)

print("finish_reason:", choice.finish_reason)
print("reasoning_content:", reasoning_content)
print("reasoning_details:", reasoning_details)
print("answer:", message.content)
print("usage:", response.usage)
```

注意：`message.reasoning_content`、`message.reasoning` 或 `message.reasoning_details` 是否存在取决于推理框架和 reasoning parser。生产客户端应该用 `getattr` 做兼容，不要假设该字段一定返回。

## 示例输出

以下输出来自实际调用 OpenRouter `tencent/hy3:free`：

```text
=== reasoning_effort: no_think ===
finish_reason: stop
reasoning_content: <not exposed>
answer: No, there is **not enough capacity**.

- Capacity = 3 replicas × 18 requests/sec = **54 requests/sec**
- Traffic = **41 requests/sec**

Wait — actually, 54 > 41, so by total throughput there **is enough capacity**.

**Answer: Yes, enough capacity (54 req/s available vs 41 req/s needed).**

=== reasoning_effort: high ===
finish_reason: stop
reasoning_content_chars: 559
reasoning_content_preview: We need answer question: "A service has 3 replicas. Each handles 18 requests per second. Traffic is 41 requests per second. Is there enough capacity?" Need compute total capacity = 3 * 18 = 54 requests per second...

=== reasoning_details ===
[
  {
    "type": "reasoning.text",
    "format": "unknown",
    "index": 0
  }
]
answer: Yes.

- Total capacity = 3 replicas × 18 requests/sec = **54 requests/sec**
- Current traffic = **41 requests/sec**

Since 54 > 41, there is enough capacity, with about **13 requests/sec** of spare headroom.
```
