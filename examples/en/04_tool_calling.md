# 04 Tool Calling

## Introduction

This example demonstrates how to let the Hy3 model perform **tool calling (Tool Calling / Function Calling)**, including:

- **Single tool call**: based on the user question, the model automatically decides which tool to call and generates the corresponding parameters.
- **Multi-turn tool loop**: uses a `while` loop to keep calling the model and executing tools — as long as the model keeps returning `tool_calls`, the tool results are fed back and the model is called again, until it gives a final natural-language answer.

Using a "query Beijing weather" scenario, the example defines a local mock function `get_weather` to show the full flow: question → model decides to call a tool → execute local function → feed result back → model generates the final answer.

---

## Prerequisites

1. The Hy3 service has been started via vLLM or SGLang, with the **tool-call parser enabled**.

   - **vLLM** (needs both the reasoning parser and auto tool choice enabled):
     ```bash
     vllm serve tencent/Hy3 \
       --tensor-parallel-size 8 \
       --tool-call-parser hy_v3 \
       --reasoning-parser hy_v3 \
       --enable-auto-tool-choice \
       --port 8000 \
       --served-model-name hy3
     ```
   - **SGLang**:
     ```bash
     python3 -m sglang.launch_server \
       --model tencent/Hy3 \
       --tp-size 8 \
       --tool-call-parser hunyuan \
       --reasoning-parser hunyuan \
       --port 8000 \
       --served-model-name hy3
     ```

2. Install dependencies:
   ```bash
   pip install openai
   ```

3. Configure connection info via environment variables (defaults suit a local deployment):
   ```bash
   # Optional; adjust as needed
   set HY3_BASE_URL=http://127.0.0.1:8000/v1
   set HY3_API_KEY=EMPTY
   ```

---

## Complete Request

```python
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
```

---

## Complete Response Parsing

### 1. The `tools` parameter structure

`tools` is a list; each element describes a tool the model may call, with the following structure:

```json
[
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
            "description": "要查询天气的城市名称，例如：北京、上海"
          }
        },
        "required": ["city"]
      }
    }
  }
]
```

- `type`: fixed as `"function"`.
- `function.name`: the tool name; when the model returns tool_calls it uses this to indicate which function to call.
- `function.description`: the tool description; the model uses this to decide when to call the tool — **the clearer the description, the more accurate the call**.
- `function.parameters`: a standard JSON Schema describing the parameter types and required fields.

### 2. `response.choices[0].message.tool_calls` structure

When the model decides to call a tool, the `message` in the response carries a `tool_calls` field (a list):

```json
{
  "id": "call_abc123",
  "type": "function",
  "function": {
    "name": "get_weather",
    "arguments": "{\"city\": \"北京\"}"
  }
}
```

- `id`: the unique identifier of this tool call; when feeding the tool result back you must use the same `tool_call_id` to match it.
- `type`: fixed as `"function"`.
- `function.name`: the name of the function the model wants to call.
- `function.arguments`: a **JSON string** (not a dict); parse it with `json.loads()` into a dict before passing it to the local function.

### 3. Execute the tool and feed the result back

After obtaining `tool_calls`, you need to do three things:

1. **Parse the arguments**: `func_args = json.loads(tool_call.function.arguments)`.
2. **Execute the local function**: dispatch by function name, e.g. `available_functions[func_name](**func_args)`.
3. **Feed the result back**: append two messages to `messages`:
   - An **assistant message** (the message returned by the model with `tool_calls`; it must be appended as-is, otherwise the model won't know which calls it made);
   - A **tool-role message** containing the tool execution result:
     ```python
     {
         "role": "tool",
         "tool_call_id": tool_call.id,
         "content": func_result,
     }
     ```
   `tool_call_id` must correspond one-to-one with the `id` from when the call was initiated.

### 4. Multi-turn tool loop logic

This example uses a `while` loop to implement multi-turn tool calling:

- After each model call, check whether `message.tool_calls` exists.
  - **Exists**: execute all tools, append the assistant message and the tool result messages to `messages`, then `continue` to the next round.
  - **Does not exist**: the model has generated the final natural-language answer based on the tool results; print `message.content` and `break`.
- To guard against accidental infinite loops, `max_iterations = 5` is set as a safety cap.

This loop structure can handle complex scenarios such as "the model calls several tools in succession" or "the model decides to call the next tool based on the previous tool's result".

---

## Sample Output

> The following is sample output (not a real run result) to illustrate the print layout of each step of the script.

```text
======================================================================
[User Question]
北京今天天气怎么样？
======================================================================

----- Round 1: calling model -----

[Tool call received]
  tool_call_id : call_0a1b2c3d
  function     : get_weather
  arguments    : {"city": "北京"}

[Executing local function get_weather]
  Result: 晴，气温 28°C，湿度 45%，西北风 3 级

----- Round 2: calling model -----

[Final Answer]
北京今天天气晴朗，气温 28°C，湿度 45%，西北风 3 级，整体比较舒适。
外出可以不用带伞，但气温略高，注意防晒和补水。
======================================================================
```
