# 04 工具调用 / Tool Calling

[中文](#中文) | [English](#english)

---

## 中文

本示例展示如何使用 Hy3 API 的**工具调用（Function Calling）** 能力，包括**单次工具调用**和**多轮工具循环**。

> **前提**：部署 vLLM 时需添加 `--tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice` 参数。

---

### 定义工具

使用 OpenAI 规范的 JSON Schema 定义可用工具：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 '北京'、'上海'"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '2 + 3 * 4'"
                    }
                },
                "required": ["expression"]
            }
        }
    }
]
```

---

### 单次工具调用

模型判断需要调用工具时，会返回 `tool_calls` 而非文本内容：

#### 请求

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "北京今天天气怎么样？"},
    ],
    tools=tools,
    temperature=0.9,
    top_p=1.0,
)

# 检查是否触发了工具调用
message = response.choices[0].message

if message.tool_calls:
    for tool_call in message.tool_calls:
        print(f"工具名：{tool_call.function.name}")
        print(f"参数：{tool_call.function.arguments}")
        # 输出：工具名：get_weather
        #       参数：{"city": "北京", "unit": "celsius"}
```

#### 执行工具并返回结果

```python
import json

# 模拟工具执行结果
def execute_tool(tool_call):
    args = json.loads(tool_call.function.arguments)
    if tool_call.function.name == "get_weather":
        return json.dumps({
            "city": args["city"],
            "temperature": 22,
            "humidity": 65,
            "condition": "晴"
        }, ensure_ascii=False)
    return json.dumps({"error": "未知工具"})

# 将工具结果加入消息历史
messages = [
    {"role": "user", "content": "北京今天天气怎么样？"},
]

# 第一轮：获取工具调用
response = client.chat.completions.create(
    model="hy3", messages=messages, tools=tools, temperature=0.9, top_p=1.0,
)
tool_call = response.choices[0].message.tool_calls[0]

# 追加助手消息（含 tool_calls）和工具结果
messages.append(response.choices[0].message)
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": execute_tool(tool_call),
})

# 第二轮：模型基于工具结果生成最终回复
final_response = client.chat.completions.create(
    model="hy3", messages=messages, tools=tools, temperature=0.9, top_p=1.0,
)
print(final_response.choices[0].message.content)
# 输出：北京今天天气晴朗，气温22°C，湿度65%，适合户外活动。
```

---

### 多轮工具循环

复杂任务中，模型可能需要连续调用多个工具：

```python
messages = [
    {"role": "user", "content": "查一下北京和上海的天气，然后计算两地的温差。"},
]

max_rounds = 5
for round_num in range(max_rounds):
    response = client.chat.completions.create(
        model="hy3", messages=messages, tools=tools, temperature=0.9, top_p=1.0,
    )
    msg = response.choices[0].message

    # 无工具调用 → 最终回复
    if not msg.tool_calls:
        print(f"最终回复：{msg.content}")
        break

    # 执行所有工具调用
    messages.append(msg)
    for tool_call in msg.tool_calls:
        result = execute_tool(tool_call)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        })
```

#### 示例输出

```
[Round 1] 调用：get_weather({"city": "北京"})
[Round 2] 调用：get_weather({"city": "上海"})
[Round 3] 调用：calculate({"expression": "abs(22 - 26)"})
最终回复：北京气温22°C，上海气温26°C，两地温差为4°C。
```

---

## English

This example demonstrates Hy3's **tool calling (function calling)** capability, including **single tool calls** and **multi-round tool loops**.

> **Prerequisite**: Deploy vLLM with `--tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice`.

---

### Define Tools

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                },
                "required": ["city"]
            }
        }
    }
]
```

### Single Tool Call

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "What's the weather in Beijing today?"}],
    tools=tools,
    temperature=0.9, top_p=1.0,
)

msg = response.choices[0].message
if msg.tool_calls:
    print(f"Tool: {msg.tool_calls[0].function.name}")
    print(f"Args: {msg.tool_calls[0].function.arguments}")
```

### Multi-Round Tool Loop

```python
messages = [{"role": "user", "content": "Check weather in Beijing and Shanghai, then calculate the temperature difference."}]

for _ in range(5):
    response = client.chat.completions.create(
        model="hy3", messages=messages, tools=tools, temperature=0.9, top_p=1.0,
    )
    msg = response.choices[0].message
    if not msg.tool_calls:
        print(f"Final: {msg.content}")
        break
    messages.append(msg)
    for tc in msg.tool_calls:
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": execute_tool(tc)})
```

#### Example Output

```
[Round 1] Call: get_weather({"city": "Beijing"})
[Round 2] Call: get_weather({"city": "Shanghai"})
[Round 3] Call: calculate({"expression": "abs(22 - 26)"})
Final: Beijing is 22°C, Shanghai is 26°C. The temperature difference is 4°C.
```
