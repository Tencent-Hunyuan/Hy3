# Tool Calling

演示 Hy3 的 OpenAI-compatible tool calling。脚本定义一个本地 `get_weather` 工具，让模型发起工具调用，客户端执行工具后再把结果发回模型，直到模型给出最终答案。

运行：

```bash
python3 examples/api/tool_calling.py
```

服务端需要启用 tool parser。vLLM 示例：

```bash
--tool-call-parser hy_v3
--enable-auto-tool-choice
```

SGLang 示例：

```bash
--tool-call-parser hunyuan
```

## 完整请求

下面展示本地 vLLM/SGLang 默认请求。使用 OpenRouter、腾讯云或其他远程 provider 时，脚本会根据 `examples/api/common.py` 的配置去掉 Hy3 本地模板参数或合并 `HY3_EXTRA_BODY_JSON`；运行时打印的 request 是实际发送内容。

工具定义：

```python
[
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a supported city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, for example Shenzhen or Beijing.",
                    }
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]
```

首轮请求：

```python
{
    "model": "hy3",
    "messages": [
        {
            "role": "user",
            "content": "Use the weather tool to check Shenzhen. Then tell me if I should bring an umbrella.",
        }
    ],
    "tools": TOOLS,
    "tool_choice": "auto",
    "temperature": 0.2,
    "top_p": 1.0,
    "max_tokens": 512,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think",
        }
    },
}
```

工具返回后追加的消息：

```python
[
    {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "arguments": "{\"city\":\"Shenzhen\"}",
                },
            }
        ],
    },
    {
        "role": "tool",
        "tool_call_id": "call_abc123",
        "name": "get_weather",
        "content": "{\"city\":\"Shenzhen\",\"condition\":\"light rain\",\"temperature_c\":29,\"humidity_percent\":82,\"umbrella_recommended\":true}",
    },
]
```

## 完整 response 解析

```python
message = response.choices[0].message
tool_calls = getattr(message, "tool_calls", None) or []

for tool_call in tool_calls:
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments or "{}")
    result = execute_tool(function_name, arguments)
```

工具循环停止条件：

- 如果 `tool_calls` 非空，执行本地工具并追加 `tool` role 消息。
- 如果 `tool_calls` 为空，读取 `message.content` 作为最终回复。
- 示例最多执行 `HY3_MAX_TOOL_ROUNDS` 轮，避免工具循环失控。

## 示例输出

以下输出来自实际调用 OpenRouter `tencent/hy3:free`：

```text
=== assistant response ===
id: gen-1783435594-K4teaUQsYk5cxiJWEYtq
model: tencent/hy3-20260706:free
finish_reason: tool_calls
content: None

=== tool_calls ===
[
  {
    "id": "chatcmpl-tool-a5d4ffc6024a0e0a",
    "function": {
      "arguments": "{\"city\": \"Shenzhen\"}",
      "name": "get_weather"
    },
    "type": "function",
    "index": 0
  }
]

=== parsed_tool_call ===
get_weather({"city": "Shenzhen"})

=== tool_result ===
{
  "city": "Shenzhen",
  "condition": "light rain",
  "temperature_c": 29,
  "humidity_percent": 82,
  "umbrella_recommended": true
}

=== final_content ===
The weather in Shenzhen right now is **light rain**, with a temperature of 29°C and humidity at 82%. The weather data also explicitly recommends bringing an umbrella.

**Yes, you should bring an umbrella** — it's currently raining lightly, so it'll keep you dry. ☔
```
