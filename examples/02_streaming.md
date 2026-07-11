# 02 流式输出 / Streaming

[中文](#中文) | [English](#english)

---

## 中文

本示例展示如何使用 Hy3 API 进行**流式请求**，实现逐 chunk 实时输出，降低首字等待时间，提升用户体验。

### 流式请求

设置 `stream=True` 后，API 返回一个迭代器，每次 yield 一个文本 chunk。

#### 请求

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "用 Python 写一个快速排序算法。"},
    ],
    temperature=0.9,
    top_p=1.0,
    stream=True,  # 开启流式输出
)
```

#### 逐 chunk 解析

```python
full_content = ""

for chunk in stream:
    # 每个 chunk 包含一个 delta（增量内容）
    delta = chunk.choices[0].delta

    # delta.content 可能为 None（如开头的 role 信息）
    if delta.content:
        print(delta.content, end="", flush=True)
        full_content += delta.content

print()  # 换行
print(f"\n完整内容长度：{len(full_content)} 字符")
```

#### 示例输出

```
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)

完整内容长度：285 字符
```

---

### 带角色信息的流式解析

每个 chunk 还包含角色信息和 finish_reason：

```python
for chunk in stream:
    choice = chunk.choices[0]

    # 第一个 chunk 通常包含 role
    if choice.delta.role:
        print(f"角色：{choice.delta.role}")

    # 最后一个 chunk 包含 finish_reason
    if choice.finish_reason:
        print(f"\n结束原因：{choice.finish_reason}")

    if choice.delta.content:
        print(choice.delta.content, end="", flush=True)
```

---

## English

This example demonstrates **streaming requests** with the Hy3 API, outputting text chunk by chunk in real time to reduce first-token latency and improve user experience.

### Streaming Request

Set `stream=True` to get an iterator that yields text chunks.

#### Request

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "Write a quicksort algorithm in Python."},
    ],
    temperature=0.9,
    top_p=1.0,
    stream=True,
)
```

#### Chunk-by-Chunk Parsing

```python
full_content = ""

for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="", flush=True)
        full_content += delta.content

print(f"\nTotal content length: {len(full_content)} chars")
```

#### Example Output

```
def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)

Total content length: 285 chars
```
