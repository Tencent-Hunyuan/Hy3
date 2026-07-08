<p align="left">
    <a href="./zh-cn/04_tool_calling.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Example 04: Tool calling

This example demonstrates both a single tool-call response and a multi-turn application-side tool loop.

> Related: [Examples Index](./README.md) | [API Quickstart](../quickstart.md)

## Server requirement

Start the server with a Hy3/Hunyuan-compatible tool parser. For vLLM, enable automatic tool choice and set the Hy3 parser. For SGLang, use its Hunyuan parser.

## Run

```bash
python examples/04_tool_calling.py
```

## Full request

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "东京现在天气怎么样？请调用工具查询，并用摄氏度回答。"}],
    tools=TOOLS,
    tool_choice="auto",
    parallel_tool_calls=False,
    temperature=0.2,
    max_tokens=800,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)
```

Tool schema excerpt:

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "parameters": {
      "type": "object",
      "properties": {
        "location": {"type": "string"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
      },
      "required": ["location", "unit"],
      "additionalProperties": false
    },
    "strict": true
  }
}
```

## Response parsing

```python
message = response.choices[0].message
for tc in message.tool_calls or []:
    name = tc.function.name
    args = json.loads(tc.function.arguments)
    result = TOOL_IMPLS[name](**args)
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "name": name,
        "content": json.dumps(result, ensure_ascii=False),
    })
```

Then call the model again with the updated `messages` so it can produce the final answer.

## Sample output

```text
=== one-call tool parsing ===
assistant content: None
tool_calls:
- name: get_weather
  arguments: {"location":"Tokyo","unit":"celsius"}

=== multi-turn tool loop ===
step 1: model requested 1 tool call(s)
executed get_weather({'location': 'Tokyo', 'unit': 'celsius'}) -> {'location': 'Tokyo', 'unit': 'celsius', 'temperature': 21, 'condition': 'partly cloudy', 'source': 'mock-weather-service'}
step 2: model requested 1 tool call(s)
executed calculator({'expression': '17 * 23'}) -> {'expression': '17 * 23', 'result': 391}
final answer: 东京当前示例天气为 21°C、多云间晴；17 * 23 = 391。
```

Actual tool-call order may vary. Always validate tool arguments before execution.
