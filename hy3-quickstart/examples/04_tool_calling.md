# 04 · Tool Calling(一次调用 + 多轮工具循环)

Hy3 支持 OpenAI Function Calling:模型自主决定调用哪个工具、传什么参数,你执行后把结果回填,多轮直到产出最终回答。可运行脚本:`04_tool_calling.py`。

---

## 1. 定义工具

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的实时天气",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名"}},
            "required": ["city"],
        },
    },
}]
```

## 2. 第一轮:让模型决定调工具

```python
messages = [{"role": "user", "content": "北京今天天气怎么样?"}]
resp = client.chat.completions.create(model="hy3", messages=messages, tools=tools)
msg = resp.choices[0].message
```

### 真实响应

```json
{
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "",
      "tool_calls": [{
        "id": "chatcmpl-tool-462bcb6f75364f4abc960ddb564f08fe",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"北京\"}"
        }
      }]
    },
    "finish_reason": "tool_calls"
  }],
  "usage": { "prompt_tokens": 201, "completion_tokens": 20, "total_tokens": 221 }
}
```

要点:`finish_reason` 变成 **`tool_calls`**,正文 `content` 为空,`tool_calls[].function.arguments` 是模型生成的 JSON 字符串参数。

## 3. 执行工具并回填,进入下一轮

```python
import json

# 把 assistant 的 tool_calls 消息原样塞回 messages
messages.append(msg)

for tc in msg.tool_calls:
    args = json.loads(tc.function.arguments)        # {"city": "北京"}
    result = get_weather(**args)                    # 你自己实现: 调真实天气 API
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,                      # 必须对上 id
        "content": json.dumps(result, ensure_ascii=False),
    })

# 第二轮: 模型基于工具结果给最终回答
resp2 = client.chat.completions.create(model="hy3", messages=messages, tools=tools)
print(resp2.choices[0].message.content)
```

---

## 多轮循环要点

- `tool_call_id` 必须**一一对应**,否则报错。
- 用 `while msg.tool_calls:` 循环,直到 `finish_reason == "stop"`(模型不再要工具,给出最终回答)。
- 一次用户提问可能触发**多个工具调用**(如「北京和上海天气」→ 两次 `get_weather`),都在同一个 `tool_calls` 数组里。

> 完整多轮循环代码见 `04_tool_calling.py`。
