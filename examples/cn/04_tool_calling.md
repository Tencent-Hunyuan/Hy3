# 04 工具调用（Tool Calling）

## 简介

本示例演示如何让 Hy3 模型进行**工具调用（Tool Calling / Function Calling）**，包括：

- **单次工具调用**：模型根据用户问题，自动判断需要调用哪个工具、生成对应参数。
- **多轮工具循环**：使用 `while` 循环持续调用模型并执行工具，只要模型继续返回 `tool_calls` 就把工具结果回传并再次调用，直到模型给出最终的自然语言回答。

示例中以"查询北京天气"为场景，定义了一个本地 mock 函数 `get_weather`，展示完整的"提问 → 模型决定调用工具 → 执行本地函数 → 回传结果 → 模型生成最终回答"流程。

---

## 前置条件

1. 已通过 vLLM 或 SGLang 启动 Hy3 服务，并**启用工具调用解析器**。

   - **vLLM**（需同时开启 reasoning 解析器与自动工具选择）：
     ```bash
     vllm serve tencent/Hy3 \
       --tensor-parallel-size 8 \
       --tool-call-parser hy_v3 \
       --reasoning-parser hy_v3 \
       --enable-auto-tool-choice \
       --port 8000 \
       --served-model-name hy3
     ```
   - **SGLang**：
     ```bash
     python3 -m sglang.launch_server \
       --model tencent/Hy3 \
       --tp-size 8 \
       --tool-call-parser hunyuan \
       --reasoning-parser hunyuan \
       --port 8000 \
       --served-model-name hy3
     ```

2. 安装依赖：
   ```bash
   pip install openai
   ```

3. 连接信息通过环境变量配置（默认值适用于本地部署）：
   ```bash
   # 可选，按需修改
   set HY3_BASE_URL=http://127.0.0.1:8000/v1
   set HY3_API_KEY=EMPTY
   ```

---

## 完整请求

> 完整可运行脚本位于 `../en/04_tool_calling.py`。

```python
"""Hy3 Example 04: Tool calling (single call + multi-turn tool loop).

Before running against a local server, start Hy3 with a tool-call parser:
  - vLLM:  --tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice
  - SGLang: --tool-call-parser hunyuan --reasoning-parser hunyuan
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common import get_config, make_client, run_tool_loop  # noqa: E402


def get_weather(city: str) -> str:
    """Return mock weather information for a given city."""
    mock_weather = {
        "北京": "晴，气温 28°C，湿度 45%，西北风 3 级",
        "上海": "多云，气温 30°C，湿度 65%，东南风 2 级",
        "广州": "雷阵雨，气温 32°C，湿度 80%，南风 4 级",
        "深圳": "阵雨，气温 31°C，湿度 78%，南风 3 级",
    }
    return mock_weather.get(city, f"{city}：暂无天气数据（mock）")


TOOLS = [
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

AVAILABLE_FUNCTIONS = {
    "get_weather": get_weather,
}


def on_tool_call(tool_call, result):
    print("\n[Tool call received]")
    print(f"  tool_call_id : {tool_call.id}")
    print(f"  function     : {tool_call.function.name}")
    print(f"  arguments    : {tool_call.function.arguments}")
    print(f"\n[Executing local function {tool_call.function.name}]")
    print(f"  Result: {result}")


def main():
    cfg = get_config()
    print(f"Connecting to {cfg['base_url']}  model={cfg['model']}")
    client = make_client()

    messages = [
        {"role": "user", "content": "北京今天天气怎么样？"},
    ]
    print("=" * 70)
    print("[User Question]")
    print(messages[0]["content"])
    print("=" * 70)

    final = run_tool_loop(
        client,
        messages,
        TOOLS,
        AVAILABLE_FUNCTIONS,
        max_iterations=5,
        reasoning="no_think",
        on_tool_call=on_tool_call,
    )

    print("\n[Final Answer]")
    print(getattr(final, "content", None) if final is not None else "(no response)")
    print("=" * 70)


if __name__ == "__main__":
    main()
```

---

## 完整 response 解析

### 1. `tools` 参数结构

`tools` 是一个列表，每个元素描述一个可被模型调用的工具，结构如下：

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

- `type`：固定为 `"function"`。
- `function.name`：工具名，模型返回 tool_calls 时用它指明要调用哪个函数。
- `function.description`：工具描述，模型据此判断何时调用该工具，**描述越清晰，调用越准确**。
- `function.parameters`：标准 JSON Schema，描述参数类型与必填项。

### 2. `response.choices[0].message.tool_calls` 结构

当模型决定调用工具时，响应里的 `message` 会带上 `tool_calls` 字段（一个列表）：

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

- `id`：本次工具调用的唯一标识，回传工具结果时必须用同一个 `tool_call_id` 对应。
- `type`：固定为 `"function"`。
- `function.name`：模型要调用的函数名。
- `function.arguments`：**JSON 字符串**（不是 dict），需要用 `json.loads()` 解析成字典后再传给本地函数。

### 3. 执行工具并回传结果

拿到 `tool_calls` 后，需要做三件事：

1. **解析参数**：`func_args = json.loads(tool_call.function.arguments)`。
2. **执行本地函数**：通过函数名分发到对应实现，例如 `available_functions[func_name](**func_args)`。
3. **回传结果**：向 `messages` 追加两条消息：
   - 一条 **assistant 消息**（就是模型返回的带 `tool_calls` 的 message，必须原样追加，否则模型不知道自己发起了哪些调用）；
   - 一条 **tool 角色消息**，包含工具执行结果：
     ```python
     {
         "role": "tool",
         "tool_call_id": tool_call.id,
         "content": func_result,
     }
     ```
   `tool_call_id` 必须与发起调用时的 `id` 一一对应。

### 4. 多轮工具循环逻辑

本示例用 `while` 循环实现多轮工具调用：

- 每轮调用模型后，检查 `message.tool_calls` 是否存在。
  - **存在**：执行所有工具，把 assistant 消息和 tool 结果消息追加到 `messages`，然后 `continue` 进入下一轮。
  - **不存在**：说明模型已根据工具结果生成最终自然语言回答，打印 `message.content` 并 `break`。
- 为防止意外死循环，设置了 `max_iterations = 5` 作为安全上限。

这种循环结构可以处理"模型连续调用多个工具"或"基于上一个工具结果再决定调用下一个工具"的复杂场景。

---

## 示例输出

> 以下为示例性输出（非真实运行结果），用于展示脚本各步骤的打印格式。

```text
======================================================================
【用户提问】
北京今天天气怎么样？
======================================================================

----- 第 1 轮调用模型 -----

【收到工具调用】
  tool_call_id : call_0a1b2c3d
  function     : get_weather
  arguments    : {"city": "北京"}

【执行本地函数 get_weather】
  结果: 晴，气温 28°C，湿度 45%，西北风 3 级

----- 第 2 轮调用模型 -----

【最终回答】
北京今天天气晴朗，气温 28°C，湿度 45%，西北风 3 级，整体比较舒适。
外出可以不用带伞，但气温略高，注意防晒和补水。
======================================================================
```
