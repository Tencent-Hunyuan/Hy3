# 04 - Tool Calling（工具调用）

演示一次工具调用与多轮工具循环。

## 说明

Hy3 支持 Function Calling，模型可以在需要时返回工具调用请求，开发者执行工具后将结果传回，模型据此生成最终回复。

## 运行方式

```bash
pip install openai python-dotenv
cp ../../.env.example ../../.env  # 编辑 .env 填入密钥
python tool_calling.py
```

## 一次工具调用

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"}
                },
                "required": ["city"]
            },
        }
    }
]

messages = [
    {"role": "user", "content": "北京今天天气怎么样？"},
]

response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    tools=tools,
    tool_choice="auto",
    temperature=0.9,
)

message = response.choices[0].message
print(f"Assistant: {message.content}")

if message.tool_calls:
    for tc in message.tool_calls:
        print(f"Tool call: {tc.function.name}({tc.function.arguments})")
```

## 多轮工具循环（完整流程）

```python
tools = [...]  # 同上

messages = [{"role": "user", "content": "北京和上海今天天气怎么样？哪个更暖和？"}]

while True:
    response = client.chat.completions.create(
        model="hy3", messages=messages, tools=tools, tool_choice="auto",
    )
    message = response.choices[0].message
    messages.append(message)

    if not message.tool_calls:
        print(f"最终回复: {message.content}")
        break

    for tc in message.tool_calls:
        print(f"调用工具: {tc.function.name}({tc.function.arguments})")
        if tc.function.name == "get_weather":
            import json
            args = json.loads(tc.function.arguments)
            # 模拟工具结果
            result = {"city": args["city"], "temperature": 28, "condition": "晴"}
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result)
            })
```

### 示例输出

```
调用工具: get_weather({"city": "北京"})
调用工具: get_weather({"city": "上海"})
最终回复: 北京今天 28°C，晴；上海今天 28°C，晴。两地温度相同，都很暖和！
```

---

完整源码：[tool_calling.py](./tool_calling.py)
