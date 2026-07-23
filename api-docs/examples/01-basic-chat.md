# Example 01: Basic Chat

单轮对话与多轮对话的基本用法。

---

## 环境准备

```bash
pip install openai
```

设置环境变量（或直接写在代码里）：

```bash
export HY3_API_KEY="your-api-key-here"
```

---

## 单轮对话

### 完整代码

```python
import os
from openai import OpenAI

# ============================================================
# 1. 创建客户端
# ============================================================
client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# ============================================================
# 2. 发送请求
# ============================================================
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "你好，请用三句话介绍一下你自己"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
)

# ============================================================
# 3. 解析响应
# ============================================================
choice = response.choices[0]

# 判断结束原因
finish_reason = choice.finish_reason  # "stop" | "length" | "tool_calls"
print(f"finish_reason: {finish_reason}")

# 获取正文
content = choice.message.content
print(f"content:\n{content}\n")

# 获取用量
usage = response.usage
print(f"prompt_tokens:     {usage.prompt_tokens}")
print(f"completion_tokens: {usage.completion_tokens}")
print(f"total_tokens:      {usage.total_tokens}")

# ============================================================
# 4. 完整 response 对象结构
# ============================================================
# response 对象主要属性：
#   response.id              → str   : 本次请求唯一 ID
#   response.object          → str   : "chat.completion"
#   response.created         → int   : Unix 时间戳
#   response.model           → str   : "hy3"
#   response.choices         → list  : 生成结果列表
#   response.usage           → object: token 用量
#
# choice 对象主要属性：
#   choice.index             → int   : 序号（通常为 0）
#   choice.finish_reason     → str   : 结束原因
#   choice.message.role      → str   : "assistant"
#   choice.message.content   → str   : 回复正文
#   choice.message.tool_calls → list / None : 工具调用（如有）
```

### 示例输出

```
finish_reason: stop
content:
你好！我是混元，是由腾讯开发的大模型。我专注于基础信息处理与逻辑响应，能为你解答问题、提供信息支持。如果有具体需求，随时告诉我哦～

prompt_tokens:     22
completion_tokens: 38
total_tokens:      60
```

---

## 多轮对话

多轮对话的核心是将之前的对话历史完整传入 `messages` 数组。

### 完整代码

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# ============================================================
# 初始化消息历史
# ============================================================
messages = [
    {"role": "system", "content": "你是一个简洁的编程助手，回复不超过3句话。"},
]

# ============================================================
# 第 1 轮
# ============================================================
messages.append({"role": "user", "content": "Python 里怎么去重一个列表？"})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    max_tokens=128,
)

assistant_reply = response.choices[0].message.content
print(f"[Round 1] User: {messages[-1]['content']}")
print(f"[Round 1] Assistant: {assistant_reply}\n")

# 把助手回复加入历史
messages.append({"role": "assistant", "content": assistant_reply})

# ============================================================
# 第 2 轮 — 追问
# ============================================================
messages.append({"role": "user", "content": "如果要保持原顺序呢？"})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    max_tokens=128,
)

assistant_reply = response.choices[0].message.content
print(f"[Round 2] User: {messages[-1]['content']}")
print(f"[Round 2] Assistant: {assistant_reply}\n")

messages.append({"role": "assistant", "content": assistant_reply})

# ============================================================
# 第 3 轮 — 继续追问
# ============================================================
messages.append({"role": "user", "content": "这两种方法哪种更快？"})

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.9,
    max_tokens=128,
)

assistant_reply = response.choices[0].message.content
print(f"[Round 3] User: {messages[-1]['content']}")
print(f"[Round 3] Assistant: {assistant_reply}\n")

# ============================================================
# 查看完整的 messages 历史
# ============================================================
print("=" * 60)
print("完整对话历史（共 {} 条消息）：".format(len(messages)))
print("=" * 60)
for i, msg in enumerate(messages):
    role = msg["role"]
    content = msg["content"][:80]
    print(f"  [{i}] {role:10s} | {content}...")
```

### 示例输出

```
[Round 1] User: Python 里怎么去重一个列表？
[Round 1] Assistant: 可用 `list(dict.fromkeys(lst))` 或 `list(set(lst))`（后者不保序）去重。若需保序且版本≥3.7，推荐前者。

[Round 2] User: 如果要保持原顺序呢？
[Round 2] Assistant: 用 `list(dict.fromkeys(lst))` 可保持原顺序去重，或 Python 3.7+ 直接用 `list(set(lst))` 也保序但可读性差。推荐 `dict.fromkeys`。

[Round 3] User: 这两种方法哪种更快？
[Round 3] Assistant: `dict.fromkeys` 通常比 `set` 转 list 略快且保序，二者均为 O(n)。建议用 `list(dict.fromkeys(lst))`。

============================================================
完整对话历史（共 6 条消息）：
============================================================
  [0] system     | 你是一个简洁的编程助手，回复不超过3句话。...
  [1] user       | Python 里怎么去重一个列表？...
  [2] assistant  | 可用 `list(dict.fromkeys(lst))` 或 `list(set(lst))`（后者不保序）去重。若需保序且版本≥3.7，推荐前者。...
  [3] user       | 如果要保持原顺序呢？...
  [4] assistant  | 用 `list(dict.fromkeys(lst))` 可保持原顺序去重，或 Python 3.7+ 直接用 `list(set(lst))` 也保序但可读性...
  [5] user       | 这两种方法哪种更快？...
```

---

## 关键要点

| 要点 | 说明 |
|:---|:---|
| **messages 数组即状态** | 多轮对话的全部上下文由 `messages` 数组传递，服务端无状态 |
| **role 顺序** | 通常以 `system` 开头（可选），然后 `user` / `assistant` 交替 |
| **token 累积** | 每轮都会重新计算全部历史 token，长对话注意控制历史长度 |
| **finish_reason** | `"stop"`（正常结束）、`"length"`（达到 max_tokens 截断）、`"tool_calls"`（触发工具调用） |
| **system prompt** | 用于设定角色、语气、规则等全局行为 |
