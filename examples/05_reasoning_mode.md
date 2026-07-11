# 05 思考模式 / Reasoning Mode

[中文](#中文) | [English](#english)

---

## 中文

本示例展示 Hy3 的**思考模式**（Reasoning Mode），通过 `reasoning_effort` 参数控制模型是否展示思维链过程。

> **前提**：部署 vLLM 时需添加 `--reasoning-parser hy_v3` 参数。

---

### 思考模式参数

| `reasoning_effort` 值 | 行为 | 适用场景 |
|:---|:---|:---|
| `"no_think"`（默认） | 直接输出结果，不展示思考过程 | 日常对话、简单问答、快速交互 |
| `"low"` | 展示简要思考过程 | 中等复杂度任务、需要一定解释 |
| `"high"` | 展示完整深度思维链 | 数学证明、编程难题、复杂推理 |

通过 `extra_body` 参数传入：

```python
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}
```

---

### 示例：no_think vs high 对比

#### no_think 模式（默认）

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

response_no_think = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "一个水池有A、B两个进水管，A管单独注满需要6小时，B管单独注满需要8小时。同时打开两管，需要多少小时注满？"}],
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

print("no_think 回复：")
print(response_no_think.choices[0].message.content)
```

**示例输出**：
```
同时开两管，每小时注水量为 1/6 + 1/8 = 7/24。
注满水池需要 24/7 ≈ 3.43 小时。
```

---

#### high 模式（深度思考）

```python
response_high = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "一个水池有A、B两个进水管，A管单独注满需要6小时，B管单独注满需要8小时。同时打开两管，需要多少小时注满？"}],
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)

# high 模式下，响应可能包含 reasoning_content（思考过程）
message = response_high.choices[0].message

# 打印思考过程（如果存在）
if hasattr(message, "reasoning_content") and message.reasoning_content:
    print("思考过程：")
    print(message.reasoning_content)
    print("\n最终答案：")

print(message.content)
```

**示例输出**：
```
思考过程：
设水池总容量为1。
A管每小时注水 1/6。
B管每小时注水 1/8。
同时开两管，每小时注水 1/6 + 1/8 = 4/24 + 3/24 = 7/24。
注满需要 1 ÷ (7/24) = 24/7 小时。
24/7 = 3小时 + 3/7小时 ≈ 3小时26分钟。

最终答案：
同时开两管，需要 24/7 ≈ 3.43 小时（约3小时26分钟）注满水池。
```

---

### 时延对比

```python
import time

# no_think 计时
t0 = time.time()
r1 = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "计算 123 * 456"}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
time_no_think = time.time() - t0

# high 计时
t0 = time.time()
r2 = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "计算 123 * 456"}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
time_high = time.time() - t0

print(f"no_think: {time_no_think:.2f}s | high: {time_high:.2f}s")
```

**示例输出**：
```
no_think: 1.23s | high: 4.56s
```

> **建议**：简单任务使用 `"no_think"` 以获得更低延迟；复杂推理任务使用 `"high"` 以获得更高准确率。

---

## English

This example demonstrates Hy3's **reasoning mode**, controlling whether the model shows its chain-of-thought process via the `reasoning_effort` parameter.

> **Prerequisite**: Deploy vLLM with `--reasoning-parser hy_v3`.

---

### Reasoning Mode Parameters

| `reasoning_effort` | Behavior | Use Case |
|:---|:---|:---|
| `"no_think"` (default) | Direct output, no reasoning trace | Casual chat, simple Q&A |
| `"low"` | Brief reasoning shown | Medium complexity tasks |
| `"high"` | Full deep chain-of-thought | Math, coding, complex reasoning |

Passed via `extra_body`:

```python
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}
```

---

### Example: no_think vs high

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")

# no_think mode
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Prove that sqrt(2) is irrational."}],
    temperature=0.9, top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
print(response.choices[0].message.content)

# high mode (shows reasoning trace)
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Prove that sqrt(2) is irrational."}],
    temperature=0.9, top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
msg = response.choices[0].message
if hasattr(msg, "reasoning_content") and msg.reasoning_content:
    print(f"Reasoning: {msg.reasoning_content}")
print(f"Answer: {msg.content}")
```

> **Tip**: Use `"no_think"` for lower latency on simple tasks; use `"high"` for better accuracy on complex reasoning.
