# Example 3: Non-Streaming vs Streaming（流式对比）

## 1.目标

对比两种模式的性能差异，测量首 token 时延（TTFT）和总耗时，帮助选择合适的请求模式。

## 2.请求示例

### Python

```python
from openai import OpenAI
from dotenv import load_dotenv
import os
import time

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

messages = [
    {"role": "user", "content": "请详细介绍一下腾讯混元大模型的主要特点和应用场景。"},
]

print("=== 性能对比测试 ===")
print("测试问题:", messages[0]["content"])
print()

print("1. 非流式请求（stream: false）")
start_time = time.time()
response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    stream=False,
)
end_time = time.time()
total_time_non_stream = end_time - start_time
content_length = len(response.choices[0].message.content)

print(f"   总耗时: {total_time_non_stream:.2f} 秒")
print(f"   响应长度: {content_length} 字符")
print(f"   输出速度: {content_length / total_time_non_stream:.1f} 字符/秒")
print()

print("2. 流式请求（stream: true）")
start_time = time.time()
first_token_received = False
first_token_time = 0
full_content = ""

stream = client.chat.completions.create(
    model="hy3",
    messages=messages,
    stream=True,
    stream_options={"include_usage": True},
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        if not first_token_received:
            first_token_time = time.time()
            first_token_received = True
        full_content += chunk.choices[0].delta.content

end_time = time.time()
total_time_stream = end_time - start_time
ttft = first_token_time - start_time
content_length_stream = len(full_content)

print(f"   首 token 时延 (TTFT): {ttft:.2f} 秒")
print(f"   总耗时: {total_time_stream:.2f} 秒")
print(f"   响应长度: {content_length_stream} 字符")
print(f"   输出速度: {content_length_stream / total_time_stream:.1f} 字符/秒")
print()

print("=== 对比结果 ===")
print(f"{'指标':<20} {'非流式':<15} {'流式':<15}")
print(f"{'首 token 时延':<20} {'N/A':<15} {f'{ttft:.2f} 秒':<15}")
print(f"{'总耗时':<20} {f'{total_time_non_stream:.2f} 秒':<15} {f'{total_time_stream:.2f} 秒':<15}")
print(f"{'输出速度':<20} {f'{content_length / total_time_non_stream:.1f} 字符/秒':<15} {f'{content_length_stream / total_time_stream:.1f} 字符/秒':<15}")
```

## 3.响应解析

### 3.1非流式响应

完整响应一次性返回，包含所有字段：

```json
{
  "id": "REPLACED_ID",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1775146513,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "腾讯混元大模型是由腾讯研发的..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 35,
    "completion_tokens": 150,
    "total_tokens": 185
  }
}
```

### 3.2流式响应

逐 chunk 返回，最后一个 chunk 包含 usage（如果启用）：

```
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"role": "assistant"}}]}
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "腾讯"}}]}
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [{"index": 0, "delta": {"content": "混元"}}]}
...
data: {"id": "REPLACED_ID", "object": "chat.completion.chunk", "created": 1779958293, "model": "hy3", "choices": [], "usage": {"prompt_tokens": 35, "completion_tokens": 150, "total_tokens": 185}}
data: [DONE]
```

## 4.示例输出

```
=== 性能对比测试 ===
测试问题: 请详细介绍一下腾讯混元大模型的主要特点和应用场景。

1. 非流式请求（stream: false）
   总耗时: 1.23 秒
   响应长度: 450 字符
   输出速度: 365.9 字符/秒

2. 流式请求（stream: true）
   首 token 时延 (TTFT): 0.45 秒
   总耗时: 1.35 秒
   响应长度: 452 字符
   输出速度: 334.8 字符/秒

=== 对比结果 ===
指标                  非流式           流式
首 token 时延          N/A              0.45 秒
总耗时                1.23 秒          1.35 秒
输出速度              365.9 字符/秒    334.8 字符/秒
```

## 5.性能分析

### 首 token 时延（TTFT）

- **定义**：从发送请求到收到第一个 token 的时间
- **流式优势**：通常比非流式快 50% 以上
- **用户感知**：流式可以让用户更快看到响应开始，体验更好

### 总耗时

- **非流式**：等待全部生成后一次性返回，总耗时较短
- **流式**：需要多次网络传输，总耗时略长（通常 5-15%）

### 适用场景

| 场景 | 推荐模式 | 原因 |
|------|----------|------|
| 实时聊天界面 | 流式 | 用户可以实时看到响应，减少等待焦虑 |
| API 调用/批处理 | 非流式 | 一次性获取完整结果，便于处理 |
| 长文本生成 | 流式 | 及时反馈，避免超时 |
| 语音合成 | 流式 | 边生成边播放，降低延迟 |

## 6.关键点

1. **流式降低首 token 时延**：用户能更快看到响应开始
2. **非流式总耗时略短**：避免多次网络传输开销
3. **根据场景选择**：实时交互用流式，批处理用非流式
4. **测量指标**：首 token 时延（TTFT）和总耗时是两个重要指标

正式测试代码请参考03_streaming_comparison.ipynb/03_streaming_comparison.py