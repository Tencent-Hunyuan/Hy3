# 04 工具调用（Tool calling）

这个示例让模型调用本地温度换算函数，再把结果交回模型生成最终答案。循环有明确的
轮数上限。完整代码见 [04_tool_calling.py](04_tool_calling.py)。

## 请求代码

`TOOLS` 使用 JSON Schema，限制 `value`、`from_unit`、`to_unit`，并设置
`additionalProperties=false`。请求为：

```python
result = run_tool_loop(
    lambda **request: create_chat_completion(client, **request),
    messages=[{
        "role": "user",
        "content": "把 68 华氏度转换为摄氏度，并简洁说明结果。",
    }],
    tools=TOOLS,
    handlers={"convert_temperature": convert_temperature},
    request_kwargs={
        "model": config.model,
        "temperature": 0,
        "max_tokens": 2048,
        "tool_choice": "auto",
        "extra_body": {
            "thinking": {"type": "enabled"},
            "reasoning_effort": "medium",
        },
    },
    max_tool_rounds=4,
)
```

每轮先解析完整 assistant message。若含 tool calls：

1. 原样把 `content`、`reasoning_content`、`tool_calls` 放回同一 assistant 消息；
2. 工具名必须在允许列表（allowlist）中；arguments 必须是 JSON object 并通过
   JSON Schema；
3. 阻止重复 call ID 或相同 `name + canonical arguments`；
4. 执行确定性的本地函数，以对应 `tool_call_id` 追加 `role=tool` 结果；
5. 最多执行 4 个 tool rounds，模型继续请求时立即失败。

## 运行结果

```powershell
python examples/api/04_tool_calling.py
```

以下输出采集于 2026-07-17，使用 TokenHub 广州入口、`model=hy3` 和 thinking
`medium`，共执行 1 轮工具调用。文档省略了动态 call ID，脚本仍会原样保存并回填：

```text
Model response 1
finish_reason: tool_calls
reasoning_content: present (reasoning_tokens=44)
tool: convert_temperature
arguments: {"value": 68, "from_unit": "fahrenheit", "to_unit": "celsius"}
local tool result: {"input": {"unit": "fahrenheit", "value": 68}, "output": {"unit": "celsius", "value": 20.0}}
usage: prompt_tokens=260, completion_tokens=84, total_tokens=344

Model response 2
finish_reason: stop
reasoning_content: present (reasoning_tokens=22)
content: 68 华氏度等于 **20 摄氏度**（精确值为 20.0°C），大约是舒适的室温。
usage: prompt_tokens=387, completion_tokens=48, total_tokens=435

Completed after 1 tool round(s).
```

换算结果来自本地函数，不是模型自行给出的数字。第二次请求收到的是经过 schema
校验和允许列表检查后追加的 `role=tool` 消息。

## 容易踩坑

- 不要直接执行模型给出的任意工具名或未经验证的 JSON。
- 回填结果时不能漏掉 `tool_call_id` 和 `reasoning_content`。
- 重复或持续失败的调用必须停止，不能无限循环。
