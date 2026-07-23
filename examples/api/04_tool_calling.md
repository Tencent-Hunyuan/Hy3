# 04 — Tool calling with a bounded loop

The model chooses tools, but application code owns execution. This example gives
Hy3 one deterministic temperature-conversion function, validates its arguments,
returns a tool result, and asks the model for the final explanation.

The server must have automatic tool selection and the Hy3 tool-call parser
enabled. See the repository deployment command before running this example.

## Run

```bash
python examples/api/04_tool_calling.py
```

## Complete request

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "convert_temperature",
            "description": "Convert a temperature between Celsius and Fahrenheit.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "to_unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["value", "to_unit"],
                "additionalProperties": False,
            },
        },
    }
]

response = client.chat.completions.create(
    model=config.model,
    messages=[
        {
            "role": "user",
            "content": "Convert 21 degrees Celsius to Fahrenheit, then explain the result.",
        }
    ],
    tools=tools,
    tool_choice="auto",
    temperature=0.0,
    max_tokens=512,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)
```

## Complete response and tool loop

A tool response normally contains an assistant message with `tool_calls` and no
final prose. Preserve that assistant message, execute every requested call, and
append results using the matching IDs:

```python
for _ in range(4):
    response = client.chat.completions.create(..., messages=messages, tools=tools)
    message = response.choices[0].message

    if not message.tool_calls:
        print(message.content)
        break

    messages.append(message.model_dump(exclude_none=True))
    for tool_call in message.tool_calls:
        arguments = json.loads(tool_call.function.arguments)
        result = convert_temperature(**arguments)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            }
        )
else:
    raise RuntimeError("tool loop exceeded its round limit")
```

The runnable script catches malformed JSON, missing arguments, and unknown tools
and returns an error object to the model rather than executing arbitrary code.

## Example output

Illustrative format:

```text
Round 1: model requested 1 tool call(s)
  convert_temperature({"value":21,"to_unit":"fahrenheit"}) -> {"value": 69.8, "unit": "°F"}
Assistant: 21°C is 69.8°F, calculated by multiplying by 9/5 and adding 32.
```

## Production checks

- Allow-list tool names; never evaluate model-generated code.
- Validate arguments again in application code even when JSON Schema is strict.
- Return one tool message for every `tool_call_id`, including error results.
- Set a round limit and per-tool timeouts.
- Require confirmation before a tool performs an external or destructive action.
