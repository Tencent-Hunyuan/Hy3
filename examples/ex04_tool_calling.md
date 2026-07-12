# 04 Tool Calling：单次调用与多轮工具循环

Hy3 支持 OpenAI 兼容的 Function Calling。本示例演示如何声明工具、解析模型返回的工具调用、执行本地函数，并将结果回传给模型完成多轮循环。

## 完整请求

```python
import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

# 本地模拟工具函数
def get_weather(city: str) -> str:
    """模拟查询天气"""
    weather_db = {
        "北京": "晴朗，25°C",
        "上海": "多云，28°C",
        "深圳": "小雨，30°C",
    }
    return weather_db.get(city, f"暂无 {city} 的天气数据")


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如北京、上海、深圳",
                    }
                },
                "required": ["city"],
            },
        },
    }
]

messages = [
    {"role": "system", "content": "你可以调用 get_weather 工具查询天气。"},
    {"role": "user", "content": "今天北京和深圳的天气怎么样？"},
]

# 第一轮：模型决定调用工具
response = client.chat.completions.create(
    model="hy3",
    messages=messages,
    tools=tools,
    tool_choice="auto",
    temperature=0.3,
)

message = response.choices[0].message
print("=== 第一轮模型输出 ===")
print(message)

# 将 assistant 消息转换为 dict 后追加到上下文
messages.append(message.model_dump())

# 执行所有工具调用，并将结果追加到上下文
if message.tool_calls:
    for tool_call in message.tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        print(f"\n调用工具: {function_name}({function_args})")

        if function_name == "get_weather":
            result = get_weather(**function_args)
        else:
            result = f"未知工具: {function_name}"

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            }
        )

    # 第二轮：模型根据工具结果生成自然语言回答
    final_response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        tools=tools,
        temperature=0.3,
    )

    print("\n=== 最终回答 ===")
    print(final_response.choices[0].message.content)
else:
    print("\n模型未调用工具，直接回答:", message.content)
```

## Response 解析

当模型决定调用工具时，`response.choices[0].message` 会包含：

- `content`：通常为 `None` 或空字符串。
- `tool_calls`：工具调用列表，每个元素包含：
  - `id`：工具调用 ID，回传结果时必须带上。
  - `function.name`：要调用的函数名。
  - `function.arguments`：JSON 字符串形式的参数。

执行工具后，需要向 `messages` 追加 `role="tool"` 的消息，并携带：

- `tool_call_id`：与对应的 tool_call.id 一致。
- `content`：工具返回的结果字符串。

## 示例输出

```text
=== 第一轮模型输出 ===
ChatCompletionMessage(content=None, role='assistant', tool_calls=[ChatCompletionMessageToolCall(id='call_xxx', function=Function(arguments='{"city":"北京"}', name='get_weather'), type='function'), ChatCompletionMessageToolCall(id='call_yyy', function=Function(arguments='{"city":"深圳"}', name='get_weather'), type='function')])

调用工具: get_weather({'city': '北京'})
调用工具: get_weather({'city': '深圳'})

=== 最终回答 ===
今天北京天气晴朗，25°C；深圳有小雨，30°C。出行请注意携带雨具。
```

## 要点提示

1. `tool_choice="auto"` 让模型自己决定是否调用工具；`"none"` 强制不调用；也可以强制指定某个工具。
2. 多轮工具循环时，每次都要将 `assistant` 的 tool_calls 和 `tool` 的结果完整回传。
3. 工具返回的 `content` 必须是字符串，复杂结果先用 `json.dumps()` 序列化。
4. 若开启思考模式且发生工具调用，后续轮次需将 `reasoning_content` 一并回传（如适用）。
