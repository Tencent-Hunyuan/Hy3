# Example 4: Tool Calling — 单次调用 & 多轮工具循环

部署时 vLLM 需 `--enable-auto-tool-choice`，SGLang 需 `--tool-call-parser hunyuan`。

## 定义工具

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的当前天气信息",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "城市名称"}
            },
            "required": ["city"],
        },
    },
}]
```

## 响应结构

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_xxx",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"北京\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

## 多轮循环

```python
for _ in range(max_rounds):
    response = client.chat.completions.create(...)
    msg = response.choices[0].message
    if not msg.tool_calls:
        break
    messages.append(msg)
    for tc in msg.tool_calls:
        result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
```

## 示例输出

```
============================================================
1. Single Tool Call
============================================================

工具调用: get_weather
参数: {"city": "北京"}
工具返回: {"city": "北京", "weather": "晴，25°C，空气质量良"}

最终回答: 北京今天天气晴朗，气温25°C，空气质量良好，适合外出活动。

============================================================
2. Multi-round Tool Calling
============================================================

--- 第 1 轮 ---
调用工具: get_weather({"city": "北京"})
工具返回: {"city": "北京", "weather": "晴，25°C，空气质量良"}
调用工具: get_weather({"city": "上海"})
工具返回: {"city": "上海", "weather": "多云，28°C，湿度 70%"}
调用工具: calculate({"expression": "(25+17)*3"})
工具返回: {"expression": "(25+17)*3", "result": 126}

--- 第 2 轮 ---
最终回答: 北京今天天气晴朗，25°C；上海多云，28°C，湿度较高。
计算 (25+17)×3 = 126。
```
