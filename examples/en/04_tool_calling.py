"""
Hy3 Tool Calling Example
========================

Demonstrates how to let the Hy3 model call local functions:
  1. Single tool call: the model decides which tool to call based on the user question
  2. Multi-turn tool loop: keep calling in a while loop until the model no longer returns tool_calls

Before running, start the Hy3 service (vLLM / SGLang) and enable the tool-call parser:
  - vLLM:  --tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice
  - SGLang: --tool-call-parser hunyuan --reasoning-parser hunyuan

Connection info is configured via environment variables (with defaults):
  HY3_BASE_URL  default http://127.0.0.1:8000/v1
  HY3_API_KEY   default EMPTY
"""

import json
import os

from openai import OpenAI

# Initialize the client via environment variables (with defaults) for easy deployment switching
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

MODEL = "hy3"


# ---------------------------------------------------------------------------
# 1. Define a local tool function: mock weather query
# ---------------------------------------------------------------------------
def get_weather(city: str) -> str:
    """Return mock weather information for a given city."""
    # Mock data for demonstration; in real projects, connect to a real weather API
    mock_weather = {
        "北京": "晴，气温 28°C，湿度 45%，西北风 3 级",
        "上海": "多云，气温 30°C，湿度 65%，东南风 2 级",
        "广州": "雷阵雨，气温 32°C，湿度 80%，南风 4 级",
        "深圳": "阵雨，气温 31°C，湿度 78%，南风 3 级",
    }
    return mock_weather.get(city, f"{city}：暂无天气数据（mock）")


# ---------------------------------------------------------------------------
# 2. Define the tool schema (OpenAI function format)
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

# Tool name -> local function mapping, for unified dispatch when the model returns any tool name
available_functions = {
    "get_weather": get_weather,
}


def call_model(messages):
    """Wrap the Hy3 call with the recommended params."""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        temperature=0.9,
        top_p=1.0,
        # no_think: respond directly; tool-calling scenarios usually don't need deep reasoning
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
    )


def main():
    # Initialize the conversation
    messages = [
        {
            "role": "user",
            "content": "北京今天天气怎么样？",
        }
    ]
    print("=" * 70)
    print("[User Question]")
    print(messages[0]["content"])
    print("=" * 70)

    # Multi-turn tool loop: keep executing and feeding back results as long as the model returns tool_calls
    # Set a max iteration count to prevent accidental infinite loops
    max_iterations = 5
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n----- Round {iteration}: calling model -----")

        response = call_model(messages)
        message = response.choices[0].message

        # Case A: the model returned tool_calls; execute the tools
        if message.tool_calls:
            # The assistant message with tool_calls must be appended to history as-is
            messages.append(message)

            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args_raw = tool_call.function.arguments
                print(f"\n[Tool call received]")
                print(f"  tool_call_id : {tool_call.id}")
                print(f"  function     : {func_name}")
                print(f"  arguments    : {func_args_raw}")

                # Parse arguments (arguments is a JSON string)
                try:
                    func_args = json.loads(func_args_raw)
                except json.JSONDecodeError as e:
                    print(f"  [Argument parsing failed] {e}")
                    func_args = {}

                # Dispatch to the local function for execution
                func_to_call = available_functions.get(func_name)
                if func_to_call is None:
                    func_result = f"错误：未找到工具 {func_name}"
                else:
                    func_result = func_to_call(**func_args)

                print(f"\n[Executing local function {func_name}]")
                print(f"  Result: {func_result}")

                # Feed the tool execution result back to the model as a role=tool message
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": func_result,
                    }
                )

            # Continue to the next round so the model can generate a reply based on the tool result
            # (it may also call tools again)
            continue

        # Case B: the model did not return tool_calls, meaning it has produced the final natural-language answer
        print("\n[Final Answer]")
        print(message.content)
        print("=" * 70)
        break

    else:
        # Hit the max iteration count without finishing; print a notice
        print("\n[Warning] Reached max iteration count; loop terminated.")


if __name__ == "__main__":
    main()
