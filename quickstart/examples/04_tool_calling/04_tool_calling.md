# Example 4: Tool Calling（工具调用）

## 1.目标

展示工具调用能力，包括一次工具调用和多轮工具循环（Agent 模式）。

## 2.工具调用原理

工具调用允许模型根据用户的请求，自动选择并调用外部工具来获取信息或执行操作。这是构建智能 Agent 的基础能力。

## 3.一次工具调用

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

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如：北京、上海、广州"
                    }
                },
                "required": ["city"]
            }
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
)

print("=== 第一次响应 ===")
print("结束原因:", response.choices[0].finish_reason)

if response.choices[0].finish_reason == "tool_calls":
    tool_call = response.choices[0].message.tool_calls[0]
    print("工具名称:", tool_call.function.name)
    print("工具参数:", tool_call.function.arguments)
    
    messages.append(response.choices[0].message)
    
    city = eval(tool_call.function.arguments)["city"]
    weather_info = f"{city}今天天气晴朗，温度25-32°C，湿度60%。"
    print(f"\n模拟调用 get_weather('{city}') 返回:", weather_info)
    
    messages.append({
        "role": "tool",
        "content": weather_info,
        "tool_call_id": tool_call.id
    })
    
    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        tools=tools,
    )
    
    print("\n=== 最终回答 ===")
    print(response.choices[0].message.content)
```

### 3.2响应解析

第一次响应（需要调用工具）：

```json
{
  "id": "REPLACED_ID",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1775146513,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "tool_calls": [
          {
            "id": "call_REPLACED_ID",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"city\": \"北京\"}"
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 25,
    "total_tokens": 145
  }
}
```

第二次响应（工具返回后生成最终回答）：

```json
{
  "id": "REPLACED_ID",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1775146513,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "北京今天天气晴朗，温度25-32°C，湿度60%。"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 180,
    "completion_tokens": 20,
    "total_tokens": 200
  }
}
```

### 3.3示例输出

```
=== 第一次响应 ===
结束原因: tool_calls
工具名称: get_weather
工具参数: {"city": "北京"}

模拟调用 get_weather('北京') 返回: 北京今天天气晴朗，温度25-32°C，湿度60%。

=== 最终回答 ===
北京今天天气晴朗，温度25-32°C，湿度60%。
```

## 4多轮工具循环（Agent 模式）

### 4.1请求示例

#### Python

```python
from openai import OpenAI
from dotenv import load_dotenv
import os
import math

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY"),
    base_url="https://tokenhub.tencentmaas.com/v1",
)

def calculate_area(radius):
    return math.pi * radius ** 2

def calculate_volume(radius):
    return (4/3) * math.pi * radius ** 3

tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_area",
            "description": "计算圆的面积",
            "parameters": {
                "type": "object",
                "properties": {
                    "radius": {
                        "type": "number",
                        "description": "圆的半径"
                    }
                },
                "required": ["radius"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_volume",
            "description": "计算球体的体积",
            "parameters": {
                "type": "object",
                "properties": {
                    "radius": {
                        "type": "number",
                        "description": "球体的半径"
                    }
                },
                "required": ["radius"]
            }
        }
    }
]

messages = [
    {"role": "user", "content": "一个半径为5的球体，它的表面积和体积分别是多少？"},
]

def run_agent():
    print("=== Agent 多轮工具循环 ===")
    print("用户问题:", messages[0]["content"])
    print()
    
    max_iterations = 5
    for i in range(max_iterations):
        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        
        finish_reason = response.choices[0].finish_reason
        message = response.choices[0].message
        
        if finish_reason == "tool_calls":
            print(f"第 {i+1} 轮: 需要调用工具")
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = eval(tool_call.function.arguments)
                print(f"  - 调用: {tool_name}({tool_args})")
                
                if tool_name == "calculate_area":
                    result = calculate_area(**tool_args)
                elif tool_name == "calculate_volume":
                    result = calculate_volume(**tool_args)
                else:
                    result = "未知工具"
                
                print(f"  - 返回: {result}")
                
                messages.append({
                    "role": "tool",
                    "content": str(result),
                    "tool_call_id": tool_call.id
                })
            
            messages.append(message)
        
        elif finish_reason == "stop":
            print(f"\n第 {i+1} 轮: 完成回答")
            print("最终回答:", message.content)
            break
    
    else:
        print("超过最大迭代次数")

run_agent()
```

### 4.2响应解析

多轮工具调用的关键是维护完整的消息历史：

```json
[
  {"role": "user", "content": "一个半径为5的球体，它的表面积和体积分别是多少？"},
  {"role": "assistant", "content": null, "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "calculate_area", "arguments": "{\"radius\": 5}"}}]},
  {"role": "tool", "content": "78.53981633974483", "tool_call_id": "call_1"},
  {"role": "assistant", "content": null, "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "calculate_volume", "arguments": "{\"radius\": 5}"}}]},
  {"role": "tool", "content": "523.5987755982989", "tool_call_id": "call_2"},
  {"role": "assistant", "content": "半径为5的球体，表面积约为78.54，体积约为523.60。"}
]
```

### 4.3示例输出

```
=== Agent 多轮工具循环 ===
用户问题: 一个半径为5的球体，它的表面积和体积分别是多少？

第 1 轮: 需要调用工具
  - 调用: calculate_area({'radius': 5})
  - 返回: 78.53981633974483

第 2 轮: 需要调用工具
  - 调用: calculate_volume({'radius': 5})
  - 返回: 523.5987755982989

第 3 轮: 完成回答
最终回答: 半径为5的球体，表面积约为78.54，体积约为523.60。
```

## 5.工具调用参数说明

| 参数 | 类型 | 说明 |
|------|------|------|
| `tools` | array | 工具定义列表 |
| `tool_choice` | string/object | 调用策略：`none`、`auto`、`required` 或指定工具 |
| `parallel_tool_calls` | bool | 是否允许并行调用多个工具 |

## 6.关键点

1. **工具定义**：每个工具需要 `type`、`function.name`、`function.description` 和 `function.parameters`
2. **检测工具调用**：检查 `finish_reason == "tool_calls"`
3. **执行工具**：解析 `tool_calls[0].function.name` 和 `tool_calls[0].function.arguments`
4. **回填结果**：将工具返回结果添加为 `tool` 角色的消息
5. **多轮循环**：重复上述步骤直到 `finish_reason == "stop"`

正式测试代码见04_tool_calling.ipynb/04_tool_calling.py