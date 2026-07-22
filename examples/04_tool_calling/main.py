"""
对应Issue要求：tool calling（一次调用+多轮工具循环）
示例工具：城市天气查询（模拟接口，无需真实API）
"""
from openai import OpenAI
import json

client = OpenAI(
    api_key="YOUR-API-KEY",
    base_url="https://tokenhub.tencentmaas.com/v1"
)

# 1. 定义工具列表（模拟天气查询接口）
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_city_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，比如北京、上海、深圳"
                    }
                },
                "required": ["city"]
            }
        }
    }
]


# 2. 模拟工具执行函数
def get_city_weather(city: str) -> str:
    """模拟天气查询，实际项目中可替换为真实天气API"""
    weather_db = {
        "北京": "晴，气温18-28℃，西北风3级",
        "上海": "多云转阴，气温22-29℃，东风2级",
        "深圳": "阵雨，气温25-31℃，南风4级"
    }
    return weather_db.get(city, f"暂不支持{city}的天气查询")


print("=== 工具调用完整流程测试 ===")
messages = [
    {"role": "user", "content": "北京今天天气怎么样？适合去爬长城吗？"}
]

# 3. 第一轮请求：模型判断是否调用工具
response1 = client.chat.completions.create(
    model="hy3-preview",
    messages=messages,
    tools=tools,
    tool_choice="auto",  # 自动决定是否调用工具
    temperature=0.7
)

message1 = response1.choices[0].message
messages.append(message1)  # 把模型回复加入历史

# 4. 解析工具调用请求
if message1.tool_calls:
    tool_call = message1.tool_calls[0]
    print(f"模型决定调用工具：{tool_call.function.name}")
    print(f"调用参数：{tool_call.function.arguments}")

    # 5. 执行工具调用
    args = json.loads(tool_call.function.arguments)
    tool_result = get_city_weather(args["city"])
    print(f"工具返回结果：{tool_result}")

    # 6. 把工具结果加入历史，发起第二轮请求
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": tool_result
    })

    # 7. 第二轮请求：模型根据工具结果生成最终回复
    response2 = client.chat.completions.create(
        model="hy3-preview",
        messages=messages,
        temperature=0.7
    )
    print(f"\n模型最终回复：{response2.choices[0].message.content}")
else:
    print(f"模型直接回复：{message1.content}")