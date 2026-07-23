# Example 02: Streaming

流式请求与逐 chunk 解析，实现打字机效果的实时输出。

---

## 环境准备

```bash
pip install openai
```

---

## 流式请求 — 基础版

### 完整代码

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# ============================================================
# 开启 stream=True
# ============================================================
stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "写一首五行诗，主题是编程"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    stream=True,  # 关键参数
)

# ============================================================
# 逐 chunk 解析
# ============================================================
print("Assistant: ", end="", flush=True)

for chunk in stream:
    # chunk 是 ChatCompletionChunk 对象
    if chunk.choices and len(chunk.choices) > 0:
        delta = chunk.choices[0].delta

        # delta.content 是本次增量文本（可能为 None）
        if delta.content:
            print(delta.content, end="", flush=True)

        # delta.role 仅第一个 chunk 有值（"assistant"）
        if delta.role:
            pass  # 通常是 "assistant"，可忽略

        # finish_reason 仅最后一个 chunk 有值
        if chunk.choices[0].finish_reason:
            finish_reason = chunk.choices[0].finish_reason
            # "stop" | "length" | "tool_calls"

print()  # 换行
```

### 示例输出（打字机效果逐字输出）

```
Assistant: 代码如诗行，
逻辑筑桥梁。
bug藏暗处，
调试迎晨光。
指尖生万象。
```

---

## 流式请求 — 进阶版（含用量统计）

Hy3 流式请求的最后一个 chunk 可能包含 `usage` 信息，用于统计 token 消耗。

### 完整代码

```python
import os
import time
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# ============================================================
# 发送流式请求
# ============================================================
start_time = time.time()

stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "解释一下什么是 Docker，100 字以内"},
    ],
    temperature=0.9,
    max_tokens=200,
    stream=True,
)

# ============================================================
# 状态变量
# ============================================================
collected_content = ""      # 累积完整内容
collected_reasoning = ""    # 累积思考过程（如有）
chunk_count = 0             # chunk 计数
first_token_time = None     # 首 token 到达时间
finish_reason = None        # 结束原因
usage = None                # token 用量

# ============================================================
# 遍历 chunks
# ============================================================
for chunk in stream:
    chunk_count += 1

    if not chunk.choices:
        continue

    choice = chunk.choices[0]
    delta = choice.delta if choice.delta else None

    if delta is None:
        continue

    # 首 token 计时
    if first_token_time is None and (getattr(delta, "content", None) or getattr(delta, "reasoning_content", None)):
        first_token_time = time.time() - start_time

    # 累积思考内容（仅 reasoning_effort != "no_think" 时可能有）
    if getattr(delta, "reasoning_content", None):
        collected_reasoning += delta.reasoning_content
        print(f"\033[90m{delta.reasoning_content}\033[0m", end="", flush=True)

    # 累积正文
    if delta.content:
        collected_content += delta.content
        print(delta.content, end="", flush=True)

    # 结束原因（仅最后一个 chunk）
    if choice.finish_reason:
        finish_reason = choice.finish_reason

    # 用量（仅最后一个 chunk 可能有）
    if hasattr(chunk, "usage") and chunk.usage:
        usage = chunk.usage

# ============================================================
# 汇总统计
# ============================================================
total_time = time.time() - start_time

print("\n")
print("=" * 50)
print("流式请求统计")
print("=" * 50)
print(f"  总耗时:        {total_time:.2f}s")
print(f"  首 token 时延: {first_token_time:.2f}s" if first_token_time else "  首 token 时延: N/A")
print(f"  chunk 数:      {chunk_count}")
print(f"  完成原因:      {finish_reason}")
if usage:
    print(f"  prompt_tokens:     {usage.prompt_tokens}")
    print(f"  completion_tokens: {usage.completion_tokens}")
    print(f"  total_tokens:      {usage.total_tokens}")
print(f"  累积内容长度:  {len(collected_content)} 字符")
```

### 示例输出

```
Docker 是一种容器化平台，可将应用及其依赖打包成轻量、可移植的容器。它基于操作系统级虚拟化，实现环境一致、快速部署与隔离，相比传统虚拟机更省资源、启动更快。

==================================================
流式请求统计
==================================================
  总耗时:        1.46s
  首 token 时延: 0.72s
  chunk 数:      26
  完成原因:      stop
  累积内容长度:  81 字符
```

---

## chunk 结构说明

每个 `chunk` 是一个 `ChatCompletionChunk` 对象：

```python
# chunk 结构（关键字段）
{
    "id": "xxxxxxxx",
    "object": "chat.completion.chunk",
    "created": 1718432000,
    "model": "hy3",
    "choices": [
        {
            "index": 0,
            "delta": {
                "content": "Docker",      # 增量文本（可为空字符串）
                "function_call": None,
                "refusal": None,
                "role": "assistant",      # 仅第一个 chunk
                "tool_calls": None,
            },
            "finish_reason": None,         # 仅最后一个 chunk 有值
        }
    ],
    "usage": None,  # 仅最后一个 chunk 可能有值
}
```

### 各字段出现时机

| 字段 | 第一个 chunk | 中间 chunks | 最后一个 chunk |
|:---|:---|:---|:---|
| `delta.role` | ✅ `"assistant"` | ❌ `None` | ❌ `None` |
| `delta.content` | ✅ | ✅ | ✅（可能为空） |
| `delta.function_call` | ❌ `None` | ❌ `None` | ❌ `None` |
| `delta.refusal` | ❌ `None` | ❌ `None` | ❌ `None` |
| `delta.tool_calls` | ✅（如有） | ✅（如有） | ❌ `None` |
| `finish_reason` | ❌ `None` | ❌ `None` | ✅ `"stop"` / `"length"` / `"tool_calls"` |
| `usage` | ❌ `None` | ❌ `None` | ✅ 或 `None` |

---

## 关键要点

| 要点 | 说明 |
|:---|:---|
| **stream=True** | 唯一的开关，设置为 `True` 即启用流式 |
| **delta.content 可能为空** | 某些 chunk 只传 role 或 tool_calls，必须判空 |
| **finish_reason 仅在末尾** | 在此之前为 `None` |
| **usage 不一定有** | 部分部署可能不返回 usage 信息 |
| **基础流式不含思考字段** | 这份示例输出里没有 `reasoning_content`，思考模式见 example 05 |
