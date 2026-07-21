# 示例 04：工具调用（一次调用 + 多轮工具循环）

> 对应脚本：[`04_tool_calling.py`](04_tool_calling.py)

让模型在需要时“调用函数”获取实时数据（天气、数据库、计算器……）。模型只**提出调用**，真正执行的是你的代码

## 前置条件（本地部署必看）

工具调用依赖服务端的工具解析器，启动时要加参数：

```bash
# vLLM
vllm serve hy3 --tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice
# SGLang
python -m sglang.launch_server --model hy3 --tool-call-parser hunyuan --reasoning-parser hunyuan
```

> `--tool-call-parser` / `--reasoning-parser` 分别启用工具调用与思考模式解析；本示例只用工具调用，但建议一并加上 reasoning parser 以便后续叠加思考模式。

未启用 `--tool-call-parser` 时，响应里 `tool_calls` 会为空（见 quickstart 第 9 节排查表）。

## 完整请求

```python
TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的当前天气",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名，如 北京"}},
            "required": ["city"],
        },
    },
}]

response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "北京今天天气怎么样？适合户外运动吗？"}],
    tools=TOOLS,
    tool_choice="auto",   # 模型自行决定是否调用工具
    temperature=0.3,
    extra_body=REASONING,
)
```

## 完整响应解析

当模型决定调用工具时，`message.tool_calls` 不为空：

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null,
      "tool_calls": [{
        "id": "call_abc",
        "type": "function",
        "function": {"name": "get_weather", "arguments": "{\"city\": \"北京\"}"}
      }]
    },
    "finish_reason": "tool_calls"
  }]
}
```

| 字段 | 含义 |
|---|---|
| `message.tool_calls[i].id` | 本次工具调用唯一 id，回填 `role="tool"` 时需要 |
| `message.tool_calls[i].function.name` | 要调用的函数名 |
| `message.tool_calls[i].function.arguments` | JSON 字符串形式的参数，需用 `json.loads` 解析 |
| `finish_reason` | 出现 `tool_calls` 表示模型在等工具结果 |

## 多轮工具循环

把 assistant 消息（含 `tool_calls`）原样加入历史，再把函数执行结果以 `role="tool"` 追加，再次调用模型，循环直到没有 `tool_calls`：

```python
messages.append({"role": "assistant", "content": msg.content or "",
                 "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
for tc in msg.tool_calls:
    try:
        args = json.loads(tc.function.arguments)
    except json.JSONDecodeError as exc:
        print(f"[参数解析失败] {exc} (原始: {tc.function.arguments})")
        continue
    result = get_weather(**args)
    messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
# 再次 create(...) ...
```

> `max_rounds` 上限（示例设为 4）防止模型无限请求工具。

## 示例输出

```
[调用工具] get_weather({'city': '北京'})
[工具结果] 晴 26°C
最终回答: 北京今天天气是**晴天，气温 26°C**，整体来说非常舒适。

**是否适合户外运动？**
✅ **很适合**。26°C 的晴天温度宜人，不冷不热，阳光充足但不过于炎热，是进行跑步、骑行、徒步、球类等户外运动的理想天气。

**小建议：**
- 紫外线可能较强，建议涂抹防晒霜、戴帽子或太阳镜；
- 运动前后注意补充水分；
- 如果是中午时段，可适当避开最强日照，选择清晨或傍晚运动体验更佳。

祝你运动愉快！🏃🌞
```
