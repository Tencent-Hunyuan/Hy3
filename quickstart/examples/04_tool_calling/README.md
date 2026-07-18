# Tool Calling（一次调用 + 多轮工具循环）

## 目标

本示例演示如何向 Hy3 声明函数工具、解析一次工具调用，以及通过“模型请求 → 本地执行工具 → 回传 `tool` 消息”的循环完成多轮工具调用。

## 前置条件

- Python 3.10+
- OpenAI Python SDK `openai>=1.0.0`，环境变量加载库 `python-dotenv>=1.0.0`
- 环境变量：`HY3_BASE_URL`、`HY3_API_KEY`、`HY3_MODEL`；可从 `quickstart/.env.example` 复制为 `quickstart/.env`
- 模型能力要求：支持 OpenAI 兼容工具调用；vLLM 需启用 `--tool-call-parser hy_v3 --enable-auto-tool-choice`，SGLang 需启用 `--tool-call-parser hunyuan`

安装依赖：

```bash
python -m pip install "openai>=1.0.0" "python-dotenv>=1.0.0"
```

示例的天气数据是本地固定数据，不会请求真实天气服务。

## 完整请求

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "返回内置示例天气数据，不访问真实天气服务。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_temperature",
            "description": "在摄氏度与华氏度之间转换温度。",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "from_unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                    "to_unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["value", "from_unit", "to_unit"],
            },
        },
    },
]

response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=TOOLS,
    tool_choice="auto",
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)
```

## 完整 Response 解析

当 `finish_reason` 为 `tool_calls` 或 `message.tool_calls` 非空时，调用方必须：

1. 保存完整 assistant 消息及其中的 `tool_calls`。
2. 用 `json.loads` 解析 `function.arguments`，并只允许调用白名单函数。
3. 执行函数，把 JSON 结果作为 `role="tool"` 消息回传，且 `tool_call_id` 必须与请求中的 ID 一致。
4. 再次请求模型；重复上述过程，直到返回普通 assistant 正文或达到最大轮数。

```python
for tool_call in message.tool_calls or []:
    arguments = json.loads(tool_call.function.arguments)
    result = TOOL_HANDLERS[tool_call.function.name](**arguments)
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result, ensure_ascii=False),
        }
    )
```

完整脚本还解析每轮的响应 ID、模型、全部 choices、正文、工具名、原始参数、结束原因和 Token 用量，并对非法 JSON、未知工具和参数错误返回结构化错误。

## 运行方式

在 `quickstart/` 目录执行：

```bash
python examples/04_tool_calling/tool_calling.py
```

## 示例输出

模型选择工具和组织正文的方式可能不同，下面仅展示典型结构。

```text
=== 一次工具调用 ===
round=1, id=chatcmpl-tool-1, model=hy3
choice[0].finish_reason=tool_calls
choice[0].content=None
tool_call: id=call_1, name=get_weather, arguments={"city":"深圳"}
tool_result[call_1]={'ok': True, 'result': {'city': '深圳', 'temperature': 28.0, 'unit': 'celsius', 'condition': '晴（内置示例数据）'}}
round=2, id=chatcmpl-tool-2, model=hy3
choice[0].finish_reason=stop
choice[0].content=深圳示例天气为晴，温度 28 摄氏度。

=== 多轮工具循环 ===
tool_call: id=call_2, name=get_weather, arguments={"city":"北京"}
tool_result[call_2]=...
tool_call: id=call_3, name=convert_temperature, arguments={"value":22,"from_unit":"celsius","to_unit":"fahrenheit"}
tool_result[call_3]={'ok': True, 'result': {'value': 71.6, 'unit': 'fahrenheit'}}
choice[0].content=北京示例温度为 22°C，换算后为 71.6°F。
```
