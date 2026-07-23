"""示例 4: 工具调用"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import get_client, MODEL

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前日期和时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["full", "date", "time"],
                        "description": "时间格式"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学运算",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "运算类型"
                    },
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["operation", "a", "b"]
            }
        }
    }
]

def get_current_time(format_type="full"):
    """模拟获取时间"""
    from datetime import datetime
    now = datetime.now()
    if format_type == "date":
        return now.strftime("%Y-%m-%d")
    elif format_type == "time":
        return now.strftime("%H:%M:%S")
    return now.strftime("%Y-%m-%d %H:%M:%S")

def calculate(operation, a, b):
    if operation == "add": return str(a + b)
    elif operation == "subtract": return str(a - b)
    elif operation == "multiply": return str(a * b)
    elif operation == "divide": return str(a / b) if b != 0 else "错误：除数不能为0"
    return "未知操作"

def main():
    print("\n🔧 Hy3 工具调用示例")
    print("="*50)
    
    client = get_client()
    
    # 测试 1: 查询时间
    print("\n📌 示例 1: 查询当前时间")
    print("-" * 30)
    
    messages = [{"role": "user", "content": "现在几点了？"}]
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
        max_tokens=200,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
    )
    
    print(f"💬 用户: {messages[0]['content']}")
    
    if response.choices[0].message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]
        func_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        
        print(f"🔧 调用工具: {func_name}({args})")
        
        if func_name == "get_current_time":
            result = get_current_time(args.get("format", "full"))
        else:
            result = "未知工具"
        
        print(f"📊 工具返回: {result}")
        
        messages.append(response.choices[0].message)
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
        
        final = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=200,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
        )
        print(f"🤖 AI 回复: {final.choices[0].message.content}")
    
    # 测试 2: 计算
    print("\n📌 示例 2: 数学计算")
    print("-" * 30)
    
    messages = [{"role": "user", "content": "25 乘以 37 等于多少？"}]
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=0.7,
        max_tokens=200,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
    )
    
    print(f"💬 用户: {messages[0]['content']}")
    
    if response.choices[0].message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        
        print(f"🔧 调用工具: calculate({args})")
        result = calculate(args["operation"], args["a"], args["b"])
        print(f"📊 计算结果: {result}")
        
        messages.append(response.choices[0].message)
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
        
        final = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=200,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}}
        )
        print(f"🤖 AI 回复: {final.choices[0].message.content}")

if __name__ == "__main__":
    main()