# 04 Tool Calling — 一次调用 + 多轮工具循环

演示 Function Calling：模型提出 `tool_calls` → 业务执行 → 回填 `role=tool` → 模型给出最终答案。

## 运行

```bash
cd examples/api
python 04_tool_calling/main.py
```

## 完整请求（第 1 轮）

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "深圳今天天气怎么样？"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "获取指定城市的当前天气",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string", "description": "城市名，如 深圳"}
          },
          "required": ["city"]
        }
      }
    }
  ],
  "tool_choice": "auto"
}
```

## 响应解析（第 1 轮）

| 字段 | 含义 |
|---|---|
| `finish_reason` | 常为 `tool_calls` |
| `message.tool_calls[].id` | 工具调用 ID，回填时必须原样使用 |
| `message.tool_calls[].function.name` | 函数名 |
| `message.tool_calls[].function.arguments` | JSON 字符串参数 |
| `message.reasoning_content` | 若开启思考，可能存在；**回写时务必保留** |

示例（2026-07-18 TokenHub 实测，tool id 已脱敏）：

```json
{
  "role": "assistant",
  "content": "",
  "tool_calls": [
    {
      "id": "chatcmpl-tool-REPLACED",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\": \"深圳\"}"
      }
    }
  ]
}
```

`finish_reason` 为 `tool_calls`。

## 完整请求（第 2 轮：工具循环）

将第 1 轮 assistant 消息（含 `reasoning_content` / `tool_calls`）与工具结果一并回填：

```json
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "深圳今天天气怎么样？"},
    {
      "role": "assistant",
      "content": "",
      "tool_calls": [
        {
          "id": "chatcmpl-tool-REPLACED",
          "type": "function",
          "function": {
            "name": "get_weather",
            "arguments": "{\"city\": \"深圳\"}"
          }
        }
      ]
    },
    {
      "role": "tool",
      "tool_call_id": "chatcmpl-tool-REPLACED",
      "content": "多云，气温 24~30°C，湿度 70%"
    }
  ],
  "tools": ["…同上…"]
}
```

## 最终响应示例（实测）

```json
{
  "role": "assistant",
  "content": "深圳今天的天气情况如下：\n\n- **天气**：多云\n- **气温**：24~30°C\n- **湿度**：70%\n\n整体来看是比较舒适的多云天气，早晚稍凉、中午偏热，出门可以根据气温变化适当增减衣物。",
  "reasoning_content": "用户问深圳今天天气怎么样，我已经调用了get_weather工具获取了深圳的天气信息……"
}
```

## 注意

- 模型只“提议”调用，真正执行在业务侧。
- 多轮循环可能继续返回 `tool_calls`，直到 `finish_reason=stop`。
- 交错式思考场景下，丢失 `reasoning_content` 可能导致思维链断裂。详见 [quickstart.md](../../../quickstart.md)。
