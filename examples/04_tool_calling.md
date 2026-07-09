# 04 Tool Calling

This example shows how to let Hy3 request a local tool, execute that tool in Python, append the tool result, and call the model again to produce the final user-facing answer.

Script: [04_tool_calling.py](04_tool_calling.py)

## Tool Definition

The example defines a local mock weather function:

```python
def get_weather(city: str) -> str:
    data = {
        "Beijing": "Sunny, 28C",
        "Shenzhen": "Cloudy, 30C",
        "Shanghai": "Light rain, 27C",
    }
    return data.get(city, "Weather data is unavailable for this city.")
```

It then exposes that function to the model with a JSON schema:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get mock weather information for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name, for example Beijing or Shenzhen.",
                    }
                },
                "required": ["city"],
            },
        },
    }
]
```

## Complete Request

The first model call sends user messages plus the available tools:

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=tools,
    tool_choice="auto",
    max_tokens=256,
)
```

If the model requests a tool, the script executes the tool locally and appends the result:

```python
messages.append(
    {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": result,
    }
)
```

The loop then calls the model again with the updated `messages`. This supports one tool call or multiple tool rounds up to the configured loop limit.

## Complete Response Parsing

Tool calling responses are parsed in two layers:

```text
response
└── choices[0]
    └── message
        ├── content = final answer, if no tool is needed
        └── tool_calls[] = requested function calls, if a tool is needed
```

For each tool call, parse the function name and JSON arguments:

```python
name = tool_call.function.name
arguments = json.loads(tool_call.function.arguments)
```

After all requested tools are executed, the final assistant answer is read from:

```python
message.content
```

## Run

```bash
python examples/04_tool_calling.py
```

## Example Output

```text
The weather in Beijing is Sunny, 28C.
```

The exact wording may vary, but the answer should include the mock weather result returned by `get_weather`.
