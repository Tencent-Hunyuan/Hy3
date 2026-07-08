### `non_streaming_vs_streaming`

#### **说明**

对比非流式和流式请求的首字延迟与总耗时，分析性能差异。

```
# 非流式 vs 流式：时延与耗时对比

本示例对比非流式（普通）和流式请求的性能差异，包括首字延迟和总耗时。

## 测试方法
1. 分别发起非流式（普通）和流式请求。
2. 记录请求开始到收到第一个 token 的时间（首字延迟）。
3. 记录总耗时。
4. 分析结果差异。

## 关键点
- 流式请求显著降低首字延迟，适合实时交互场景。
- 非流式请求总耗时可能更短，但用户体验受首字延迟影响。
```

**代码块 (**`**non_streaming_vs_streaming.py)**`

```python
from openai import OpenAI
import time

client = OpenAI(api_key="YOUR_API_KEY", base_url="https://tokenhub.tencentmaas.com/v1")

# 非流式请求
start = time.time()
response_non_streaming = client.chat.completions.create(
    model="hunyuan-turbo", messages=[{"role": "user", "content": "什么是量子纠缠？"}]
)
non_streaming_latency = time.time() - start
non_streaming_total = time.time() - start
print(f"非流式：首字延迟 {non_streaming_latency:.3f} 秒，总耗时 {non_streaming_total:.3f} 秒")
print(response_non_streaming.choices[0].message.content)

# 流式请求
start = time.time()
response_streaming = client.chat.completions.create(
    model="hunyuan-turbo", messages=[{"role": "user", "content": "什么是量子纠缠？"}], stream=True
)
first_token_time = None
for chunk in response_streaming:
    if chunk.choices[0].delta.content is not None:
        first_token_time = time.time()
        break
streaming_latency = first_token_time - start
streaming_total = time.time() - start
print(f"流式：首字延迟 {streaming_latency:.3f} 秒，总耗时 {streaming_total:.3f} 秒")
```

**示例输出**

```
非流式：首字延迟 0.800 秒，总耗时 1.200 秒
量子纠缠是量子力学中的现象...
流式：首字延迟 0.200 秒，总耗时 1.500 秒
```