### `tool_calling`

#### **说明**

通过 `tools` 参数调用外部工具，并处理多轮工具调用循环。

```
# 工具调用示例：单次与循环调用

本示例展示如何通过 `tools` 参数配置工具调用，并处理多轮调用流程。

## 使用说明
1. 定义工具描述（如计算器、搜索引擎）。
2. 在消息中添加 `function` 指令触发工具。
3. 模型解析工具结果并生成回复。

## 关键点
- 工具调用需明确 `type`（如 `function`）和 `description`。
- 多轮调用需维护上下文，确保工具状态连贯。
```

**代码块 (**`**tool_calling.py)**`

```python
from openai import OpenAI

client = OpenAI(api_key="YOUR_API_KEY", base_url="https://tokenhub.tencentmaas.com/v1")

# 工具调用配置
tools = [
    {
        "type": "function",
        "id": "calculator",
        "name": "计算器",
        "description": "执行数学计算（例如：2 + 3 * 4）"
    }
]

# 单次工具调用
messages = [
    {"role": "user", "content": "计算 2 + 3 * 4"},
    {"role": "assistant", "content": "需要调用计算器工具。"},
]
response = client.chat.completions.create(model="hunyuan-turbo", messages=messages, tools=tools)
print(response.choices[0].message.tool_calls[0].function.name)
print(response.choices[0].message.content)

# 多轮工具调用循环（示例：持续计算）
messages.append({"role": "user", "content": "结果再加 5"})
response = client.chat.completions.create(model="hunyuan-turbo", messages=messages, tools=tools)
print(response.choices[0].message.content)
```

**示例输出**

```
计算器
结果为 14。
结果再加 5 后为 19。
```