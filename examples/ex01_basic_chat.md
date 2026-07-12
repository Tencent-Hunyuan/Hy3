# 01 Basic Chat：单轮与多轮对话

本示例演示如何使用 Hy3 完成最简单的单轮对话，以及如何维护 `messages` 上下文进行多轮对话。

## 完整请求

```python
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# 单轮对话
single_turn = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "请用一句话介绍 Hy3。"},
    ],
    temperature=0.7,
    max_tokens=256,
)

print("=== 单轮对话 ===")
print(single_turn.choices[0].message.content)
print("finish_reason:", single_turn.choices[0].finish_reason)

# 多轮对话：将 assistant 回复追加到 messages，继续提问
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "请用一句话介绍 Hy3。"},
]

first_response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.7,
    max_tokens=256,
)

assistant_msg = first_response.choices[0].message
messages.append({"role": "assistant", "content": assistant_msg.content})
messages.append({"role": "user", "content": "它适合哪些应用场景？"})

second_response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    temperature=0.7,
    max_tokens=512,
)

print("\n=== 多轮对话 ===")
print("Assistant 1:", assistant_msg.content)
print("Assistant 2:", second_response.choices[0].message.content)
```

## Response 解析

- `response.choices[0].message.content`：模型生成的文本内容。
- `response.choices[0].finish_reason`：生成结束原因，常见值：
  - `stop`：遇到停止词或自然结束；
  - `length`：达到 `max_tokens` 上限；
  - `content_filter` / `sensitive`：内容审核命中。
- `response.usage`：token 用量统计（`prompt_tokens`、`completion_tokens`、`total_tokens`）。

## 示例输出

```text
=== 单轮对话 ===
Hy3 是腾讯混元团队发布的 295B 总参数、21B 激活参数的 MoE 语言模型，支持 256K 长上下文与工具调用。
finish_reason: stop

=== 多轮对话 ===
Assistant 1: Hy3 是腾讯混元团队发布的 295B 总参数、21B 激活参数的 MoE 语言模型，支持 256K 长上下文与工具调用。
Assistant 2: Hy3 适合代码生成与重构、长文档理解与摘要、多轮对话与客服、Agent 工具调用、数学推理与复杂问题求解等场景。
```

## 要点提示

1. `system` 角色可选，若存在必须位于 `messages` 最前面。
2. `user` 与 `assistant` 需交替出现，多轮对话时不要把上下文顺序写反。
3. 控制 `max_tokens` 可避免生成长度不可控的回复。
