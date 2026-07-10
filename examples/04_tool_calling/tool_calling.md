# 示例 4：工具调用（Function Calling）

## 概述

演示 Hy3 的工具调用（Function Calling）能力，使模型能够调用外部工具/API 来完成任务。

两种模式：

- **单次调用**：模型识别需要调用工具，返回函数名和参数
- **多轮工具循环**：完整闭环 —— 模型调工具 → 执行工具 → 返回结果 → 模型综合回答

---

## 工具定义

本示例定义了两个工具：

### 1. get_weather —— 获取天气

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "获取指定城市的当前天气信息",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {
          "type": "string",
          "description": "城市名称，如 北京、上海、深圳"
        },
        "unit": {
          "type": "string",
          "enum": ["celsius", "fahrenheit"],
          "description": "温度单位，默认为 celsius"
        }
      },
      "required": ["city"]
    }
  }
}
```

### 2. calculate —— 数学计算

```json
{
  "type": "function",
  "function": {
    "name": "calculate",
    "description": "执行数学计算",
    "parameters": {
      "type": "object",
      "properties": {
        "expression": {
          "type": "string",
          "description": "数学表达式，如 123 * 456"
        }
      },
      "required": ["expression"]
    }
  }
}
```

---

## 多轮工具循环的消息流

```text
User: 帮我计算 12345 × 6789 的结果，然后查一下深圳的天气，最后用中文总结一下。
        │
        ▼
[1] POST /v1/chat/completions  (messages + tools)
        │
        ▼
    ← 响应: assistant.tool_calls → [{calculate(...)}, {get_weather(...)}]
        │
        ▼
[2] 执行 calculate(12345 * 6789) → 83810205
   执行 get_weather(深圳) → {"temperature": 30, "condition": "阵雨"}
        │
        ▼
[3] POST /v1/chat/completions  (追加 tool 消息)
        │
        ▼
    ← 响应: assistant.content → "计算结果：83,810,205。深圳：30°C，阵雨..."
```

---

## 运行结果示例

```text
============================================================
【工具调用示例 1：单次调用】
============================================================

模型选择调用工具: get_weather
参数: {"city": "北京"}
工具返回: {"city": "北京", "temperature": 28, "condition": "晴", "humidity": 45}


============================================================
【工具调用示例 2：多轮工具循环】
============================================================
User: 帮我计算 12345 × 6789 的结果，然后查一下深圳的天气，
最后用中文总结一下。

--- 第 1 轮 ---
  🔧 调用工具: calculate({"expression": "12345 * 6789"})
  ✅ 结果: {"expression": "12345 * 6789", "result": 83810205}
  🔧 调用工具: get_weather({"city": "深圳"})
  ✅ 结果: {"city": "深圳", "temperature": 30, "condition": "阵雨", "humidity": 80}

--- 第 2 轮 ---

  💬 最终回答:
  好的，以下是汇总结果：

  1. **计算结果**：12345 × 6789 = **83,810,205**
  2. **深圳天气**：温度 30°C，阵雨，湿度 80%

  总结：计算结果是 83,810,205。深圳目前有阵雨，出门请带伞。

--- 完整消息历史共 6 条 ---
  [0] system: 你是一个有用的助手，可以使用工具来帮助用户。
  [1] user: 帮我计算 12345 × 6789 的结果...
  [2] assistant:  (含工具调用)
  [3] tool: {"expression":"12345 * 6789","result":83810205}
  [4] tool: {"city":"深圳","temperature":30,"condition":"阵雨","humidity":80}
  [5] assistant: 好的，以下是汇总结果：...
```

---

## 消息格式详解

### assistant 消息含工具调用时

```python
messages.append({
    "role": "assistant",
    "content": "",  # 工具调用时 content 通常为空
    "tool_calls": [
        {
            "id": "call_xxx",           # 工具调用 ID，需与 tool 消息匹配
            "type": "function",         # 固定值
            "function": {
                "name": "get_weather",  # 工具名
                "arguments": '{...}',   # JSON 字符串参数
            },
        }
    ],
})
```

### tool 消息（工具返回结果）

```python
messages.append({
    "role": "tool",
    "tool_call_id": "call_xxx",  # 与对应 tool_calls 的 id 一致
    "content": json_result,      # 工具执行结果（字符串）
})
```

---

## 关键要点

1. **tools 定义需精确**：参数描述越清晰，模型调用越准确
2. **多轮循环需防死循环**：设置最大轮数（如 5 轮）
3. **tool_choice 控制**：
   - `"auto"`：模型自行决定是否调用工具
   - `"required"`：强制模型调用某个工具
   - `{"type":"function","function":{"name":"xxx"}}`：强制调用指定工具
4. **工具结果必须是字符串**：`json.dumps()` 序列化后再传入
5. **tool_call_id 必须匹配**：assistant 消息中的 `id` 与 tool 消息的 `tool_call_id` 需一一对应

---

## 参考

- [Quickstart - 参数说明](../Quickstart.md#核心参数说明)
- [TokenHub 控制台](https://console.cloud.tencent.com/tokenhub/apikey)
