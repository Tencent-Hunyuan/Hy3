# Example 04: Tool Calling

演示 Hy3 的函数调用能力：单次工具调用和完整的多轮工具循环。

---

## 环境准备

```bash
pip install openai
```

---

## 单次工具调用

最简单的场景：用户问一个问题，模型返回一个工具调用。

### 完整代码

```python
import json
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# ============================================================
# 1. 定义工具
# ============================================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名，例如 北京、上海、深圳",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位，默认 celsius",
                    },
                },
                "required": ["city"],
            },
        },
    }
]

# ============================================================
# 2. 发送请求
# ============================================================
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "北京今天天气怎么样？"},
    ],
    tools=tools,
    tool_choice="auto",  # 让模型自行决定是否调用工具
    temperature=0.9,
)

# ============================================================
# 3. 解析响应
# ============================================================
choice = response.choices[0]
message = choice.message

print(f"finish_reason: {choice.finish_reason}")
print(f"message.role:  {message.role}")
print(f"message.content: {message.content}")  # 无工具调用时有值
print()

# ============================================================
# 4. 处理工具调用
# ============================================================
if message.tool_calls:
    for i, tc in enumerate(message.tool_calls):
        print(f"--- Tool Call #{i} ---")
        print(f"  id:        {tc.id}")
        print(f"  type:      {tc.type}")
        print(f"  name:      {tc.function.name}")
        print(f"  arguments: {tc.function.arguments}")
```

### 示例输出

```
finish_reason: tool_calls
message.role:  assistant
message.content: None

--- Tool Call #0 ---
  id:        call_abc123
  type:      function
  name:      get_weather
  arguments: {"city": "北京", "unit": "celsius"}
```

---

## 多轮工具循环

真实场景：用户提问 → 模型调用工具 → 开发者执行工具 → 把结果传回 → 模型生成最终回复。

### 完整代码

```python
import json
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "YOUR_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# ============================================================
# 1. 定义工具集
# ============================================================
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "发送邮件给指定收件人",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "收件人邮箱"},
                    "subject": {"type": "string", "description": "邮件主题"},
                    "body": {"type": "string", "description": "邮件正文"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]

# ============================================================
# 2. 模拟的工具执行函数（实际场景替换为真实 API 调用）
# ============================================================
def execute_tool(tool_name: str, arguments: dict) -> str:
    """执行具体的工具并返回结果字符串"""
    print(f"  🔧 执行工具: {tool_name}({json.dumps(arguments, ensure_ascii=False)})")

    if tool_name == "get_weather":
        city = arguments.get("city", "")
        # 模拟天气数据（实际场景调用天气 API）
        weather_data = {
            "北京": "晴，25°C，湿度 40%",
            "上海": "多云，28°C，湿度 65%",
            "深圳": "阵雨，30°C，湿度 80%",
        }
        return weather_data.get(city, f"未找到{city}的天气数据")

    elif tool_name == "send_email":
        # 模拟发送邮件
        return f"邮件已发送至 {arguments.get('to')}，主题：{arguments.get('subject')}"

    return json.dumps({"error": f"未知工具: {tool_name}"})


# ============================================================
# 3. 多轮工具循环
# ============================================================
def chat_with_tools(user_message: str, max_turns: int = 5):
    """完整的工具调用循环，支持多轮、多工具调用"""
    messages = [{"role": "user", "content": user_message}]
    total_tokens = 0

    for turn in range(max_turns):
        print(f"\n{'='*50}")
        print(f"Turn {turn + 1}")
        print(f"{'='*50}")

        # 3a. 调用模型
        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.9,
        )

        choice = response.choices[0]
        message = choice.message
        total_tokens += response.usage.total_tokens

        print(f"  finish_reason: {choice.finish_reason}")
        print(f"  tokens: {response.usage.total_tokens}")

        # 3b. 如果模型直接回复（无工具调用），对话结束
        if choice.finish_reason != "tool_calls" or not message.tool_calls:
            print(f"\n✅ 最终回复:\n{message.content}")
            break

        # 3c. 处理工具调用
        print(f"  tool_calls: {len(message.tool_calls)} 个")

        # 把 assistant 消息（含 tool_calls）加入历史
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ],
        })

        # 3d. 执行每个工具调用，把结果作为 tool 消息加入
        for tc in message.tool_calls:
            tool_name = tc.function.name
            arguments = json.loads(tc.function.arguments)
            result = execute_tool(tool_name, arguments)
            print(f"  📤 结果: {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

        # 3e. 继续下一轮，让模型基于工具结果生成回复或再次调用工具

    else:
        print("\n⚠️ 达到最大轮次限制，对话终止")

    print(f"\n📊 总 token 消耗: {total_tokens}")
    return messages


# ============================================================
# 4. 运行示例
# ============================================================
if __name__ == "__main__":
    # 场景：需要先查天气再决定是否发邮件
    messages = chat_with_tools("先查一下北京天气，然后发邮件给 boss@example.com 告诉他今天的天气情况")
```

### 示例输出

```
==================================================
Turn 1
==================================================
  finish_reason: tool_calls
  tokens: 341
  tool_calls: 1 个
  🔧 执行工具: get_weather({"city": "北京"})
  📤 结果: 晴，25°C，湿度 40%

==================================================
Turn 2
==================================================
  finish_reason: tool_calls
  tokens: 421
  tool_calls: 1 个
  🔧 执行工具: send_email({"to": "boss@example.com", "subject": "北京今日天气情况", "body": "老板您好，今天北京天气为晴，气温25°C，湿度40%，天气状况良好。"})
  📤 结果: 邮件已发送至 boss@example.com，主题：北京今日天气情况

==================================================
Turn 3
==================================================
  finish_reason: stop
  tokens: 484

✅ 最终回复:
已完成：

- 北京今日天气：晴，25°C，湿度 40%
- 已将天气情况通过邮件发送给 boss@example.com，主题为「北京今日天气情况」

📊 总 token 消耗: 1246

```



---

## 关键要点

| 要点 | 说明 |
|:---|:---|
| **tool_choice** | `"auto"`（默认）：模型自行决定；`"none"`：不调用；`"required"`：强制调用 |
| **多轮循环** | 每轮检查 `finish_reason`，若为 `"tool_calls"` 则执行工具并将结果追加到 messages |
| **messages 结构** | assistant(tool_calls) → tool(result) → assistant(tool_calls) → tool(result) → ... → assistant(final) |
| **tool_call_id** | 必须严格匹配，工具结果通过 `tool_call_id` 与对应调用关联 |
| **并行工具调用** | 模型可一次返回多个 tool_calls，需要全部执行后一次性传回 |
| **错误处理** | 工具执行失败时，将错误信息作为 tool 消息返回，让模型自行恢复 |
| **流式 tool_calls** | 增量返回 id / name / arguments，需自行累积拼接 |
| **token 注意** | tool definitions 计入 prompt_tokens，工具定义越精简越好 |
