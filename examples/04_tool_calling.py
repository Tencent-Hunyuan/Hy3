"""
Hy3 工具调用（Tool Calling）示例
==============================

演示如何让 Hy3 模型调用本地函数：
  1. 单次工具调用：模型根据用户问题决定调用哪个工具
  2. 多轮工具循环：使用 while 循环持续调用，直到模型不再返回 tool_calls

运行前请先启动 Hy3 服务（vLLM / SGLang），并启用工具调用解析器：
  - vLLM:  --tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice
  - SGLang: --tool-call-parser hunyuan --reasoning-parser hunyuan

连接信息通过环境变量配置（带默认值）：
  HY3_BASE_URL  默认 http://127.0.0.1:8000/v1
  HY3_API_KEY   默认 EMPTY
"""

import json
import os

from openai import OpenAI

# 通过环境变量初始化客户端（带默认值），方便切换部署地址
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"


# ---------------------------------------------------------------------------
# 1. 定义本地工具函数：模拟天气查询
# ---------------------------------------------------------------------------
def get_weather(city: str) -> str:
    """返回某个城市的模拟天气信息。"""
    # 这里用 mock 数据演示，实际项目中可对接真实天气 API
    mock_weather = {
        "北京": "晴，气温 28°C，湿度 45%，西北风 3 级",
        "上海": "多云，气温 30°C，湿度 65%，东南风 2 级",
        "广州": "雷阵雨，气温 32°C，湿度 80%，南风 4 级",
        "深圳": "阵雨，气温 31°C，湿度 78%，南风 3 级",
    }
    return mock_weather.get(city, f"{city}：暂无天气数据（mock）")


# ---------------------------------------------------------------------------
# 2. 定义工具 schema（OpenAI function 格式）
# ---------------------------------------------------------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的实时天气信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "要查询天气的城市名称，例如：北京、上海",
                    }
                },
                "required": ["city"],
            },
        },
    }
]

# 工具名 -> 本地函数的映射，方便模型返回任意工具名时统一分发
available_functions = {
    "get_weather": get_weather,
}


def call_model(messages):
    """统一封装对 Hy3 的调用，固定使用推荐参数。"""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        temperature=0.9,
        top_p=1.0,
        # no_think：直接响应，工具调用场景一般不需要深度思考
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )


def main():
    # 初始化对话
    messages = [
        {
            "role": "user",
            "content": "北京今天天气怎么样？",
        }
    ]
    print("=" * 70)
    print("【用户提问】")
    print(messages[0]["content"])
    print("=" * 70)

    # 多轮工具循环：只要模型返回 tool_calls 就继续执行并回传结果
    # 设置最大迭代次数，防止意外死循环
    max_iterations = 5
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n----- 第 {iteration} 轮调用模型 -----")

        response = call_model(messages)
        message = response.choices[0].message

        # 情况 A：模型返回了 tool_calls，需要执行工具
        if message.tool_calls:
            # 必须把带 tool_calls 的 assistant 消息原样追加到历史中
            messages.append(message)

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args_raw = tool_call.function.arguments
                print(f"\n【收到工具调用】")
                print(f"  tool_call_id : {tool_call.id}")
                print(f"  function     : {func_name}")
                print(f"  arguments    : {func_args_raw}")

                # 解析参数（arguments 是 JSON 字符串）
                try:
                    func_args = json.loads(func_args_raw)
                except json.JSONDecodeError as e:
                    print(f"  [参数解析失败] {e}")
                    func_args = {}

                # 分发到本地函数执行
                func_to_call = available_functions.get(func_name)
                if func_to_call is None:
                    func_result = f"错误：未找到工具 {func_name}"
                else:
                    func_result = func_to_call(**func_args)

                print(f"\n【执行本地函数 {func_name}】")
                print(f"  结果: {func_result}")

                # 把工具执行结果以 role=tool 的消息回传给模型
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": func_result,
                    }
                )

            # 继续下一轮，让模型基于工具结果生成回复（可能还会再次调用工具）
            continue

        # 情况 B：模型没有返回 tool_calls，说明已经生成最终自然语言回答
        print("\n【最终回答】")
        print(message.content)
        print("=" * 70)
        break

    else:
        # 触发最大迭代次数仍未结束，给出提示
        print("\n[警告] 已达到最大迭代次数，循环终止。")


if __name__ == "__main__":
    main()
