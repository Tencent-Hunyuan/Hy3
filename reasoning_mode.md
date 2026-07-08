### `reasoning_mode`

#### **说明**

对比开启/关闭推理模式，展示模型思考过程的输出差异。

```
# 推理模式示例：思考过程开关对比

本示例展示如何开启推理模式以获取模型的中间思考步骤，便于调试或解释。

## 使用说明
1. 通过设置 `presence="human"` 开启推理模式。
2. 关闭时仅返回最终答案。
3. 分析思考过程对结果的影响。

## 关键点
- 推理模式适用于需要解释模型决策的场景。
- 可能增加响应长度和耗时，但提升透明度。
```

**代码块 (**`**reasoning_mode.py)**`

```python
from openai import OpenAI

client = OpenAI(api_key="YOUR_API_KEY", base_url="https://tokenhub.tencentmaas.com/v1")

# 关闭推理模式
response_default = client.chat.completions.create(
    model="hunyuan-turbo",
    messages=[{"role": "user", "content": "5! 的计算结果是多少？"}]
)

# 开启推理模式（设置 presence="human"）
messages = [{"role": "user", "content": "5! 的计算结果是多少？"}]
response_with_think = client.chat.completions.create(
    model="hunyuan-turbo",
    messages=messages,
    presence="human",
)

# 输出结果
print("关闭推理模式：")
print(f"用户：{messages[0]['content']}")
print(f"助手：{response_default.choices[0].message.content}")
print("开启推理模式：")
print(f"用户：{messages[0]['content']}")
print(response_with_think.choices[0].message.content)
```

**示例输出**

```
关闭推理模式：
用户：5! 的计算结果是多少？
助手：120。
开启推理模式：
用户：5! 的计算结果是多少？
我开始计算 5 的阶乘。首先，阶乘的定义是从 1 乘以到该数本身。所以 5! = 5 × 4 × 3 × 2 × 1。先算 5 × 4 得 20，再乘 3 得 60，接着乘 2 得 120，最后乘 1 不变。所以结果是 120。
```