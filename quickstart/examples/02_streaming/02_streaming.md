# Example 2: Streaming（流式请求）

## 1目标

展示流式响应的处理方式，理解 SSE（Server-Sent Events）格式和逐 chunk 解析逻辑。

## 2流式请求原理

当设置 `stream: true` 时，模型会将响应分成多个 chunk 逐次返回，而不是一次性返回完整结果。这可以显著降低首 token 时延，提升用户体验。

## 3请求示例

### cURL

```bash
curl -X POST 'https://tokenhub.tencentmaas.com/v1/chat/completions' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "请写一段关于人工智能发展的简短介绍。"}
    ],
    "stream": true,
    "stream_options": {"include_usage": true}
  }'
```

### Python

```python
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "请写一段关于人工智能发展的简短介绍。"},
    ],
    stream=True,
    stream_options={"include_usage": True},
)

print("=== 流式响应 ===")
full_content = ""
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        content = chunk.choices[0].delta.content
        full_content += content
        print(content, end="", flush=True)
    if chunk.usage:
        print("\n\n=== Token 使用 ===")
        print(f"输入: {chunk.usage.prompt_tokens} tokens")
        print(f"输出: {chunk.usage.completion_tokens} tokens")
        print(f"总计: {chunk.usage.total_tokens} tokens")

print("\n\n=== 完整响应 ===")
print(full_content)
```

## 4响应解析

流式响应以 SSE 格式返回，每一行以 `data:` 开头：

```
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"role": "assistant"}}]}

data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "人工"}}]}

data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "智能"}}]}

data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "是"}}]}

data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "一门"}}]}

data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "研究如何使计算机模拟人类智能行为的学科。"}}]}

data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [], "usage": {"prompt_tokens": 24, "completion_tokens": 32, "total_tokens": 56, "prompt_tokens_details": {"cached_tokens": 0}, "completion_tokens_details": {"reasoning_tokens": 0}}}

data: [DONE]
```

**SSE 响应字段说明：**

| 字段 | 说明 |
|------|------|
| `id` | 请求唯一标识，与非流式响应一致 |
| `object` | 对象类型，固定为 `chat.completion.chunk` |
| `choices[0].delta.role` | 助手角色，仅在第一个 chunk 中出现 |
| `choices[0].delta.content` | 当前 chunk 的文本内容 |
| `choices[0].finish_reason` | 结束原因，仅在最后一个内容 chunk 中出现 |
| `usage` | Token 使用统计，仅在 `stream_options.include_usage: true` 时出现 |
| `[DONE]` | 响应结束标记 |

## 5示例输出

```
=== 流式响应 ===
人工智能是一门研究如何使计算机模拟人类智能行为的学科。它涵盖了机器学习、深度学习、自然语言处理、计算机视觉等多个领域。近年来，随着大数据和计算能力的提升，AI技术取得了飞速发展，从AlphaGo击败围棋世界冠军到ChatGPT等大语言模型的出现，人工智能正在深刻改变着我们的生活和工作方式。

=== Token 使用 ===
输入: 24 tokens
输出: 128 tokens
总计: 152 tokens

=== 完整响应 ===
人工智能是一门研究如何使计算机模拟人类智能行为的学科。它涵盖了机器学习、深度学习、自然语言处理、计算机视觉等多个领域。近年来，随着大数据和计算能力的提升，AI技术取得了飞速发展，从AlphaGo击败围棋世界冠军到ChatGPT等大语言模型的出现，人工智能正在深刻改变着我们的生活和工作方式。
```

## 6流式 vs 非流式对比

| 特性 | 非流式 | 流式 |
|------|--------|------|
| 响应方式 | 一次性返回完整结果 | 逐 token 增量返回 |
| 首 token 时延 | 较高（等待全部生成） | 较低（立即开始返回） |
| 用户体验 | 需要等待完整响应 | 实时显示，体验更好 |
| 带宽消耗 | 单次大传输 | 多次小传输 |
| 适用场景 | 批处理、API 调用 | 实时对话、聊天界面 |

## 7关键点

1. **开启流式**：设置 `stream: true`
2. **获取 usage**：设置 `stream_options: {"include_usage": true}`
3. **逐 chunk 处理**：遍历 stream 对象，提取 `chunk.choices[0].delta.content`
4. **缓存完整内容**：需要自行拼接所有 chunk 的 content
5. **结束标记**：最后一个 chunk 的 `finish_reason` 为 `stop`，且会收到 `[DONE]`

正式测试代码请参考02_streaming.ipynb/02_streaming.py