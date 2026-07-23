from openai import OpenAI
import os
import json

client = OpenAI(
    base_url="https://hy3.example.com/v1",
    api_key=os.getenv("HY3_API_KEY", "你的API_KEY")
)

# 定义工具函数：模拟查询天气
def get_weather(city: str) -> str:
    """模拟查询指定城市的天气"""
    weather_data = {
        "北京": "晴，25℃，风力2级",
        "上海": "多云，28℃，风力3级",
        "深圳": "阵雨，30℃，风力4级"
    }
    return weather_data.get(city, f"暂无{city}的天气数据")

# 工具定义（传给模型的函数描述）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如北京、上海"
                    }
                },
                "required": ["city"]
            }
        }
    }
]

# ========== 1. 单次工具调用示例 ==========
def single_tool_call():
    print("=== 单次工具调用 ===")
    messages = [{"role": "user", "content": "北京今天天气怎么样？"}]
    
    resp = client.chat.completions.create(
        model="hy3-base",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    msg = resp.choices[0].message
    # 解析模型返回的工具调用
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        print(f"模型调用工具：{func_name}，参数：{func_args}")
        
        # 执行工具函数
        result = get_weather(func_args["city"])
        print(f"工具返回结果：{result}")
    print()

# ========== 2. 多轮工具循环完整流程 ==========
def multi_turn_tool_loop():
    print("=== 多轮工具循环完整流程 ===")
    messages = [{"role": "user", "content": "帮我查一下上海的天气，然后用通俗的话总结一下"}]
    
    # 第一轮：请求模型，触发工具调用
    resp = client.chat.completions.create(
        model="hy3-base",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    msg = resp.choices[0].message
    messages.append(msg)
    
    # 执行所有工具调用并把结果回传给模型
    if msg.tool_calls:
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            result = get_weather(func_args["city"])
            
            # 把工具结果加入对话历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": func_name,
                "content": result
            })
    
    # 第二轮：模型基于工具结果生成最终回答
    final_resp = client.chat.completions.create(
        model="hy3-base",
        messages=messages
    )
    
    final_answer = final_resp.choices[0].message.content
    print("用户问题：帮我查一下上海的天气，然后用通俗的话总结一下")
    print("模型最终回答：", final_answer)

if __name__ == "__main__":
    single_tool_call()
    multi_turn_tool_loop()
