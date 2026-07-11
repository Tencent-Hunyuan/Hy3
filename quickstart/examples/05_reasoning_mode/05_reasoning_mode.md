# Example 5: Reasoning Mode（思考模式）

## 1.目标

展示思考模式对输出质量的影响，对比开启和关闭思考模式的差异。

## 2.思考模式原理

思考模式允许模型在生成最终答案前先进行推理，提升复杂任务的准确性和可解释性。通过 `thinking` 参数控制开关，通过 `reasoning_effort` 参数控制推理深度。

## 3.开启 vs 关闭思考模式

### 3.1请求示例

#### Python

```python
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

messages = [
    {"role": "user", "content": "小明有5个苹果，给了小红2个，又买了3个，最后还剩几个？"},
]

print("=== 思考模式对比 ===")
print("问题:", messages[0]["content"])
print()

print("1. 关闭思考模式（thinking: disabled）")
response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    extra_body={"thinking": {"type": "disabled"}},
)

msg = response.choices[0].message
print("回答:", msg.content)
if hasattr(msg, "reasoning_content"):
    print("思考过程:", getattr(msg, "reasoning_content"))
else:
    print("思考过程: 无（思考模式已关闭）")
print(f"Token 消耗: {response.usage.total_tokens}")
print()

print("2. 开启思考模式（thinking: enabled）")
response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    extra_body={"thinking": {"type": "enabled"}},
)

msg = response.choices[0].message
print("回答:", msg.content)
if hasattr(msg, "reasoning_content"):
    print("思考过程:", getattr(msg, "reasoning_content"))
print(f"Token 消耗: {response.usage.total_tokens}")
```

### 3.2响应解析

**关闭思考模式：**

```json
{
  "id": "REPLACED_ID",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1775146546,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "小明最后还剩6个苹果。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 31,
    "completion_tokens": 12,
    "total_tokens": 43
  }
}
```

**开启思考模式：**

```json
{
  "id": "REPLACED_ID",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1775146546,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "小明最后还剩6个苹果。",
        "reasoning_content": "我们被问到：\"小明有5个苹果，给了小红2个，又买了3个，最后还剩几个？\" 这是一个简单的算术问题。让我们一步步来：\n\n1. 小明一开始有5个苹果。\n2. 他给了小红2个，所以剩下：5 - 2 = 3个苹果。\n3. 然后他又买了3个苹果，所以现在有：3 + 3 = 6个苹果。\n\n所以最后还剩6个苹果。\n\n答案：6。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 31,
    "completion_tokens": 132,
    "total_tokens": 163
  }
}
```

### 3.3示例输出

```
=== 思考模式对比 ===
问题: 小明有5个苹果，给了小红2个，又买了3个，最后还剩几个？

1. 关闭思考模式（thinking: disabled）
回答: 小明最后还剩6个苹果。
思考过程: 无（思考模式已关闭）
Token 消耗: 43

2. 开启思考模式（thinking: enabled）
回答: 小明最后还剩6个苹果。
思考过程: 我们被问到："小明有5个苹果，给了小红2个，又买了3个，最后还剩几个？" 这是一个简单的算术问题。让我们一步步来：

1. 小明一开始有5个苹果。
2. 他给了小红2个，所以剩下：5 - 2 = 3个苹果。
3. 然后他又买了3个苹果，所以现在有：3 + 3 = 6个苹果。

所以最后还剩6个苹果。

答案：6。
Token 消耗: 163
```

## 推理深度配置

### 3.4请求示例

#### Python

```python
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

messages = [
    {"role": "user", "content": "请详细分析一下为什么天空是蓝色的。"},
]

print("=== 推理深度对比 ===")
print("问题:", messages[0]["content"])
print()

for effort in ["low", "medium", "high"]:
    print(f"{effort} 推理深度")
    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        extra_body={"reasoning_effort": effort},
    )
    
    msg = response.choices[0].message
    print("回答:", msg.content[:100], "..." if len(msg.content) > 100 else "")
    if hasattr(msg, "reasoning_content"):
        reasoning = getattr(msg, "reasoning_content")
        print("思考过程:", reasoning[:80], "..." if len(reasoning) > 80 else "")
    print(f"Token 消耗: {response.usage.total_tokens}")
    print()
```

### 3.5示例输出

```
=== 推理深度对比 ===
问题: 请详细分析一下为什么天空是蓝色的。

low 推理深度
回答: 天空之所以是蓝色的，是因为太阳光中的蓝光波长较短，更容易被大气...
思考过程: 用户问为什么天空是蓝色的。这涉及到光的散射。蓝光波长较短...
Token 消耗: 120

medium 推理深度
回答: 天空呈现蓝色是由于瑞利散射现象。太阳光包含多种颜色的光，其中蓝...
思考过程: 用户想知道天空为什么是蓝色的。首先，我需要回忆相关的物理知识...
Token 消耗: 280

high 推理深度
回答: 天空之所以呈现蓝色，主要是由于大气中的分子对太阳光的瑞利散射所...
思考过程: 用户问为什么天空是蓝色的。这个问题看似简单，但实际上涉及光...
Token 消耗: 450
```

## 4参数说明

| 参数 | 值 | 说明 |
|------|------|------|
| `thinking.type` | `enabled` | 开启思考模式 |
| `thinking.type` | `disabled` | 关闭思考模式 |
| `reasoning_effort` | `low` | 轻量推理，速度快 |
| `reasoning_effort` | `medium` | 平衡模式，适合大多数任务 |
| `reasoning_effort` | `high` | 深度推理，适合复杂任务 |

**注意**：在 Python OpenAI SDK 中，`thinking` 和 `reasoning_effort` 需要通过 `extra_body` 参数传递。

## 5适用场景

| 场景 | 推荐配置 | 原因 |
|------|----------|------|
| 简单问答 | `thinking: disabled` 或 `reasoning_effort: low` | 速度快，token 消耗少 |
| 日常对话 | `reasoning_effort: low` | 平衡效果和成本 |
| 代码生成 | `reasoning_effort: medium` 或 `high` | 需要一定的逻辑推理 |
| 复杂推理 | `thinking: enabled` + `reasoning_effort: high` | 确保准确性 |

## 6关键点

1. **开启思考模式**：`extra_body={"thinking": {"type": "enabled"}}`
2. **关闭思考模式**：`extra_body={"thinking": {"type": "disabled"}}`
3. **控制推理深度**：`extra_body={"reasoning_effort": "high"}`
4. **获取思考过程**：通过 `getattr(msg, "reasoning_content")` 获取
5. **权衡成本**：思考模式会增加 token 消耗和响应时间

正式测试代码请参考05_reasoning_mode.ipynb/05_reasoning_mode.py