# 03 流式 vs 非流式对比 / Streaming vs Non-Streaming Comparison

[中文](#中文) | [English](#english)

---

## 中文

本示例对比 Hy3 API 的**非流式**和**流式**两种调用方式，量化首 token 时延（TTFT）和总耗时，帮助你选择合适的调用模式。

### 核心差异

| 维度 | 非流式（`stream=False`） | 流式（`stream=True`） |
|:---|:---|:---|
| 首 token 等待 | 等待全部生成完毕才返回 | 首个 token 生成后立即返回 |
| 总耗时 | 略短（无分块传输开销） | 略长（网络分块传输） |
| 用户体验 | 等待时间长，一次性输出 | 逐字输出，感知更快 |
| 适用场景 | 后端批处理、日志分析 | 聊天界面、实时交互 |

---

### 请求与计时

```python
import time
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

prompt = "请详细介绍Python中的装饰器模式，包括使用场景和代码示例。"

# ---- 非流式 ----
t0 = time.time()
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9,
    top_p=1.0,
    stream=False,
)
non_stream_time = time.time() - t0

# ---- 流式 ----
t0 = time.time()
first_token_time = None
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9,
    top_p=1.0,
    stream=True,
)
full_content = ""
for chunk in stream:
    if chunk.choices[0].delta.content:
        if first_token_time is None:
            first_token_time = time.time() - t0
        full_content += chunk.choices[0].delta.content
stream_time = time.time() - t0
```

---

### 结果输出

```python
print(f"{'指标':<20} {'非流式':>12} {'流式':>12}")
print("-" * 48)
print(f"{'首 token 时延':<20} {non_stream_time:>10.2f}s {first_token_time:>10.2f}s")
print(f"{'总耗时':<20} {non_stream_time:>10.2f}s {stream_time:>10.2f}s")
print(f"{'内容长度':<20} {len(response.choices[0].message.content):>10} {len(full_content):>10}")
```

#### 示例输出

```
指标                   非流式          流式
------------------------------------------------
首 token 时延            8.32s        0.85s
总耗时                   8.32s        9.10s
内容长度                  1024         1024
```

> **结论**：流式模式的首 token 时延显著更低（通常快 5-10 倍），适合实时交互场景；非流式总耗时略短，适合无需逐步展示的后端任务。

---

## English

This example compares **non-streaming** and **streaming** modes of the Hy3 API, measuring first-token latency (TTFT) and total time to help you choose the right approach.

### Key Differences

| Aspect | Non-Streaming (`stream=False`) | Streaming (`stream=True`) |
|:---|:---|:---|
| First token wait | Waits until full generation | Returns immediately when first token is ready |
| Total time | Slightly shorter (no chunking overhead) | Slightly longer (network chunking) |
| User experience | Long wait, all-at-once output | Progressive output, feels faster |
| Best for | Backend batch, log analysis | Chat UI, real-time interaction |

---

### Request & Timing

```python
import time
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

prompt = "Explain the decorator pattern in Python with use cases and code examples."

# ---- Non-streaming ----
t0 = time.time()
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9, top_p=1.0, stream=False,
)
non_stream_time = time.time() - t0

# ---- Streaming ----
t0 = time.time()
first_token_time = None
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9, top_p=1.0, stream=True,
)
full_content = ""
for chunk in stream:
    if chunk.choices[0].delta.content:
        if first_token_time is None:
            first_token_time = time.time() - t0
        full_content += chunk.choices[0].delta.content
stream_time = time.time() - t0
```

#### Example Output

```
Metric                Non-Stream    Streaming
------------------------------------------------
First token latency      8.32s        0.85s
Total time               8.32s        9.10s
Content length            1024         1024
```

> **Conclusion**: Streaming has significantly lower first-token latency (typically 5-10x faster), ideal for interactive use cases. Non-streaming has slightly shorter total time, better for backend tasks where output is consumed all at once.
