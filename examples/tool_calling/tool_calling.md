# 工具调用示例

## 功能说明

本示例演示如何使用 Hy3 API 进行工具调用，包括单次工具调用和多轮工具循环。

## 前置条件

1. 安装依赖：`pip install openai python-dotenv`
2. 创建 `.env` 文件，配置 API 密钥：
   ```
   API_KEY=your_api_key
   BASE_URL=https://tokenhub.tencentmaas.com/v1
   ```

## 工具定义

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"},
                },
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "获取指定股票的当前价格",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "股票代码"},
                },
                "required": ["symbol"],
            },
        },
    },
]
```

## 单次工具调用

### 请求参数

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "北京今天天气怎么样？"}],
    tools=tools,
)
```

### Response 解析

当模型决定调用工具时，`finish_reason` 为 `"tool_calls"`：

```python
print(f"响应 ID: {response.id}")
print(f"finish_reason: {response.choices[0].finish_reason}")

message = response.choices[0].message
if message.tool_calls:
    for tc in message.tool_calls:
        print(f"\n工具调用:")
        print(f"  name: {tc.function.name}")
        print(f"  arguments: {tc.function.arguments}")
        
        args = json.loads(tc.function.arguments)
        result = mock_tool_call(tc.function.name, args)
        print(f"  工具执行结果: {result}")
```

### 示例输出

```
=== 单次工具调用示例 ===

【完整请求参数】
  model: hy3
  messages: [{'role': 'user', 'content': '北京今天天气怎么样？'}]
  tools: [3 个工具]

【完整 Response 解析】
  id: chatcmpl-xxx
  choices: 1
  finish_reason: tool_calls
  message.role: assistant
  message.tool_calls:
    [0] id=call_xxx, type=function
      function.name: get_weather
      function.arguments: {"city":"北京"}
      [模拟工具执行结果]: {"city": "北京", "temperature": 25, "condition": "晴", "humidity": 60}
```

## 多轮工具循环

### 实现逻辑

多轮工具调用需要循环执行以下步骤：

1. 发送请求，获取工具调用指令
2. 执行工具，获取结果
3. 将工具结果加入对话历史
4. 再次发送请求，直到收到最终回复

### 代码实现

```python
messages = [
    {"role": "user", "content": "帮我计算一下：100乘以20%，然后用这个结果查询苹果公司的股票价格"},
]

max_rounds = 5
round_count = 0

print(f"初始问题: {messages[0]['content']}")

while round_count < max_rounds:
    def get_role(msg):
        if isinstance(msg, dict):
            return msg.get("role")
        return msg.role
    round_count += 1
    print(f"\n--- 第 {round_count} 轮 ---")

    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        tools=tools,
    )

    choice = response.choices[0]
    message = choice.message

    if choice.finish_reason == "tool_calls" and message.tool_calls:
        for tc in message.tool_calls:
            print(f"  工具调用: {tc.function.name}({tc.function.arguments})")

            args = json.loads(tc.function.arguments)
            tool_result = mock_tool_call(tc.function.name, args)
            print(f"  工具返回: {tool_result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": tool_result,
            })
    else:
        print(f"  最终回复: {message.content}")
        break

print(f"\n总轮数: {round_count}")
tool_count = len([m for m in messages if get_role(m) == "tool"])
print(f"  工具调用次数: {tool_count}")
```

### 示例输出

```
=== 多轮工具循环示例 ===

【完整对话流程】
初始问题: 帮我计算一下：100乘以20%，然后用这个结果查询苹果公司的股票价格

--- 第 1 轮 ---
  工具调用: calculate({"expression":"100*0.2"})
  工具返回: {"expression": "100*0.2", "result": 20.0}

--- 第 2 轮 ---
  工具调用: get_stock_price({"symbol":"AAPL"})
  工具返回: {"symbol": "AAPL", "price": 150.50, "change": "+2.3%"}

--- 第 3 轮 ---
  最终回复: 计算结果是20。苹果公司(AAPL)当前股价为150.50美元，涨幅+2.3%。

【多轮工具循环总结】
  总轮数: 3
  工具调用次数: 2
```

## 关键要点

1. **工具定义**：必须包含 `type`、`function.name`、`function.description` 和 `function.parameters`
2. **finish_reason**：工具调用时为 `"tool_calls"`，最终回复时为 `"stop"`
3. **工具结果**：必须以 `role: "tool"` 的形式加入对话历史
4. **tool_call_id**：必须与工具调用时的 `id` 对应
5. **安全性**：执行工具前应验证参数，避免注入攻击

## 运行方式

```bash
export API_KEY=your_api_key
export BASE_URL=https://tokenhub.tencentmaas.com/v1
python tool_calling.py
```