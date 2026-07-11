from openai import OpenAI
from dotenv import load_dotenv
import os
import math
import json

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

def single_tool_call():
    print("=== 一次工具调用示例 ===")
    messages = [
        {"role": "user", "content": "北京今天天气怎么样？"},
    ]

    weather_tool = [
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
                            "description": "城市名称"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    ]

    response = client.chat.completions.create(
        model="hy3",
        messages=messages,
        tools=weather_tool,
        tool_choice="auto",
    )

    print("=== 第一次响应 ===")
    print("结束原因:", response.choices[0].finish_reason)

    if response.choices[0].finish_reason == "tool_calls":
        tool_call = response.choices[0].message.tool_calls[0]
        print("工具名称:", tool_call.function.name)
        print("工具参数:", tool_call.function.arguments)
        
        messages.append(response.choices[0].message)
        
        city = json.loads(tool_call.function.arguments)["city"]
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
            tools=weather_tool,
        )
        
        print("\n=== 最终回答 ===")
        print(response.choices[0].message.content)

def multi_round_tool_calling():
    print("\n=== 多轮工具循环示例 ===")
    messages = [
        {"role": "user", "content": "一个半径为5的球体，它的表面积和体积分别是多少？"},
    ]

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
                tool_args = json.loads(tool_call.function.arguments)
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

if __name__ == "__main__":
    single_tool_call()
    multi_round_tool_calling()