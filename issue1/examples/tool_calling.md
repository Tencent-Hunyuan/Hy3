# Tool Calling — 函数调用与多轮工具循环

演示 Hy3 的 OpenAI 兼容 Function Calling 能力。脚本模拟一个「天气查询」场景：用户提问 → 模型识别需调工具 → 客户端执行工具 → 将结果返回模型 → 模型生成最终回答。

## 运行

```bash
cd issue1
python examples/tool_calling.py
```

## 工具定义

工具遵循 OpenAI Function Calling 规范：

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",              # 函数名
            "description": "查询指定城市的实时天气信息。",  # 描述（帮助模型判断何时调用）
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如 深圳、北京、上海",
                    }
                },
                "required": ["city"],           # 必填参数
            },
        },
    }
]
```

### 工具定义最佳实践

| 要点 | 说明 |
|:---|:---|
| **描述要具体** | `description` 决定了模型能否正确判断何时调用工具 |
| **参数要有约束** | 使用 `enum`、`required` 等约束减少模型幻觉 |
| **精简参数** | 只暴露必需参数，多余的会增加模型选择难度 |
| **一个工具一个职责** | 符合 KISS 原则，避免一个工具做太多事情 |

## 请求结构

```python
response = client.chat.completions.create(
    model="hy3-preview",
    messages=messages,
    tools=TOOLS,            # 工具定义列表
    tool_choice="auto",     # auto / none / required / 指定工具
    temperature=0.2,        # 工具调用场景推荐低温度
    top_p=1.0,
    max_tokens=512,
)
```

### tool_choice 选项

| 值 | 行为 |
|:---|:---|
| `"auto"` | **推荐**。模型自行决定是否调工具 |
| `"none"` | 禁止调用工具 |
| `"required"` | 强制调用工具（确保至少一次 tool call） |
| `{"type": "function", "function": {"name": "xxx"}}` | 强制调用指定工具 |

## 完整工具调用流程

```
用户提问
   │
   ▼
┌─────────────────────┐
│  第 1 轮：发送请求    │  messages=[user_msg]
│  模型返回 tool_calls  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  客户端执行工具       │  get_weather("深圳") → {temp_c: 29, ...}
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  第 2 轮：追加结果    │  messages += [assistant_msg, tool_result_msg]
│  模型返回最终回答     │
└─────────────────────┘
```

关键代码：

```python
# 1. 检查模型是否要求调用工具
if message.tool_calls:
    # 2. 记录 assistant 消息（含 tool_calls）
    messages.append({
        "role": "assistant",
        "content": message.content,
        "tool_calls": [{"id": tc.id, "type": tc.type,
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments}}
                       for tc in message.tool_calls]
    })

    # 3. 执行每个工具并将结果追加到 messages
    for tc in message.tool_calls:
        result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result, ensure_ascii=False)
        })

    # 4. 继续下一轮请求，直到模型不再返回 tool_calls
```

## 示例输出

以下为实际调用 TokenHub `hy3-preview` 的输出：

```
用户提问: 请帮我查一下深圳的天气，然后告诉我是否需要带伞。
可用工具: get_weather(深圳/北京/上海)

────────────────────────────────────────
第 1 轮请求
  finish_reason: tool_calls
  content: None
  tool_calls 数量: 1

  🔧 调用工具: get_weather({"city": "深圳"})
  📋 工具返回: {"city": "深圳", "condition": "小雨", "temp_c": 29, "humidity": 82, "umbrella": true}

────────────────────────────────────────
第 2 轮请求
  finish_reason: stop
  content: 深圳今天是小雨天气，气温29°C，湿度82%。出门建议带上雨伞，以防淋湿。
  tool_calls 数量: 0

============================================================
【最终回答】
============================================================
深圳今天是小雨天气，气温29°C，湿度82%。出门建议带上雨伞，以防淋湿。
```

## 关键要点

1. **温度参数**：工具调用场景推荐 `temperature=0.2`，确保模型稳定选择工具而非随机跳过
2. **死循环保护**：务必设置 `MAX_ROUNDS` 防止模型持续要求调工具
3. **JSON 解析容错**：工具参数可能不是合法 JSON，需要 try/except
4. **tool_call_id 匹配**：tool 消息的 `tool_call_id` 必须与 assistant 消息中的 `id` 严格对应
5. **并行工具调用**：模型可能一次返回多个 `tool_calls`，需要全部处理后再继续
