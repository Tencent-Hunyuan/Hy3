# 04 — Tool calling

目标：让模型提出一次只读温度换算工具调用，并通过有边界的 assistant → tool →
assistant 循环得到最终答案。完整代码见 [04_tool_calling.py](04_tool_calling.py)。

## 完整请求

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
2. 工具名必须在 allowlist；arguments 必须是 JSON object 并通过 JSON Schema；
3. 阻止重复 call ID 或相同 `name + canonical arguments`；
4. 执行确定性的本地函数，以对应 `tool_call_id` 追加 `role=tool` 结果；
5. 最多执行 4 个 tool rounds，模型继续请求时立即失败。

## 运行与真实输出

```powershell
python examples/api/04_tool_calling.py
```

2026-07-17 在 TokenHub 广州入口以 `model=hy3`、thinking `medium` 实测完成 1 个
tool round。发布样本省略动态 call ID，但脚本在实际消息历史中原样保留并回填该 ID：

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

这里的工具结果来自本地确定性函数，不是模型自行声称的换算值；第二次模型请求收到
的是已通过 schema 校验、allowlist 执行后追加的 `role=tool` 消息。

常见错误：直接执行任意模型工具名、未验证 JSON、遗漏 `tool_call_id`、丢失
`reasoning_content`、同一失败调用无限循环。
