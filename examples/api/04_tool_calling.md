# Tool Calling

This example demonstrates Hy3 tool calling with the OpenAI-compatible API.

It covers:

* defining a function tool with JSON Schema
* receiving and parsing `tool_calls`
* decoding function arguments
* executing a local Python function
* returning the tool result with `role="tool"`
* completing a multi-turn tool execution loop

> Note: This example uses mock weather data for demonstration. It does not call a live weather service.

## Prerequisites

Before running this example, make sure you have:

* Python 3.10 or later
* the `openai` Python package installed
* access to a Hy3 OpenAI-compatible endpoint with tool calling support

The example reads:

```text
HY3_BASE_URL
HY3_API_KEY
HY3_MODEL
```

If these variables are not set, it uses:

```text
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
```

## Run the example

From the repository root:

```bash
python examples/api/04_tool_calling.py
```

## Tool definition

The example defines a `get_weather` function tool:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get mock weather data for a city "
                "for tool-calling demonstration."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": (
                            "City name, for example Tokyo."
                        ),
                    }
                },
                "required": ["city"],
                "additionalProperties": False,
            },
        },
    }
]
```

The JSON Schema tells the model:

* the available function name
* what the function is intended to do
* which arguments it accepts
* which arguments are required

The model does not directly execute the Python function.

Instead, it may return a structured tool call describing which function should be invoked and with which arguments.

## Local tool implementation

The example uses deterministic mock weather data:

```python
def get_weather(city: str) -> dict[str, Any]:
    mock_weather = {
        "Tokyo": {
            "temperature_c": 28,
            "condition": "Sunny",
        },
        "Shanghai": {
            "temperature_c": 31,
            "condition": "Cloudy",
        },
        "Beijing": {
            "temperature_c": 30,
            "condition": "Clear",
        },
    }

    weather = mock_weather.get(
        city,
        {
            "temperature_c": 25,
            "condition": "Unknown",
        },
    )

    return {
        "city": city,
        **weather,
    }
```

This keeps the example focused on the tool-calling workflow without requiring a third-party weather API key.

## Single tool call

The first part of the example asks Hy3 to select an appropriate tool:

```python
messages = [
    {
        "role": "user",
        "content": (
            "What is the weather in Tokyo? "
            "Use the available tool."
        ),
    }
]
```

Complete request:

```python
request_payload = {
    "model": model,
    "messages": messages,
    "tools": tools,
    "temperature": 0.9,
    "top_p": 1.0,
    "extra_body": {
        "chat_template_kwargs": {
            "reasoning_effort": "no_think"
        }
    },
}

response = client.chat.completions.create(
    **request_payload
)
```

## Parsing the tool call

The assistant message is read from:

```python
message = response.choices[0].message
```

Tool calls are available through:

```python
message.tool_calls
```

The example checks whether any tool call was returned:

```python
if not message.tool_calls:
    print("No tool call was returned.")
    return
```

Each tool call contains:

* a tool call ID
* a function name
* JSON-encoded arguments

The example parses them as follows:

```python
for tool_call in message.tool_calls:
    print(f"Tool call ID: {tool_call.id}")
    print(
        "Function name:",
        tool_call.function.name,
    )
    print(
        "Raw arguments:",
        tool_call.function.arguments,
    )

    arguments = json.loads(
        tool_call.function.arguments
    )
```

For example, Hy3 may return:

```json
{
  "name": "get_weather",
  "arguments": "{\"city\": \"Tokyo\"}"
}
```

After `json.loads()`, the arguments become a Python dictionary:

```python
{
    "city": "Tokyo"
}
```

## Example single-call output

An observed Hy3 API response produced:

```text
=== Parsed tool calls ===
Tool call ID: chatcmpl-tool-example
Function name: get_weather
Raw arguments: {"city": "Tokyo"}
Parsed arguments: {'city': 'Tokyo'}
```

The exact tool call ID varies between requests.

## Multi-turn tool loop

The complete tool loop consists of several steps:

```text
User request
    ↓
Hy3 returns a tool call
    ↓
Client parses function name and arguments
    ↓
Python executes the local tool
    ↓
Client sends the tool result back to Hy3
    ↓
Hy3 generates the final answer
```

### Step 1: Request a tool call

The first request includes the user message and tool definitions:

```python
first_response = client.chat.completions.create(
    **first_request
)
```

Hy3 may return a response with:

```text
finish_reason = "tool_calls"
```

and a structured function call.

### Step 2: Preserve the assistant tool-call message

The assistant message must remain in conversation history:

```python
messages.append(
    assistant_message.model_dump(
        exclude_none=True
    )
)
```

This preserves the model's request to call the function.

### Step 3: Parse and execute the function

The example reads the function name:

```python
function_name = tool_call.function.name
```

and parses the JSON arguments:

```python
arguments = json.loads(
    tool_call.function.arguments
)
```

For the supported tool:

```python
if function_name == "get_weather":
    tool_result = get_weather(
        city=arguments["city"]
    )
```

An example local result is:

```json
{
  "city": "Tokyo",
  "temperature_c": 28,
  "condition": "Sunny"
}
```

### Step 4: Add the tool result

The tool result is appended to conversation history:

```python
messages.append(
    {
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": json.dumps(
            tool_result,
            ensure_ascii=False,
        ),
    }
)
```

The `tool_call_id` connects this result to the specific tool call requested by the assistant.

For example:

```json
{
  "role": "tool",
  "tool_call_id": "chatcmpl-tool-example",
  "content": "{\"city\": \"Tokyo\", \"temperature_c\": 28, \"condition\": \"Sunny\"}"
}
```

### Step 5: Send the updated conversation back to Hy3

The second request includes:

1. the original user message
2. the assistant tool-call message
3. the tool execution result

```python
final_response = client.chat.completions.create(
    **second_request
)
```

Hy3 can then use the tool result to generate a natural-language answer.

## Example output

The following behavior was observed during a Hy3 API run:

```text
=== Parsed tool calls ===
Function name: get_weather
Raw arguments: {"city": "Tokyo"}
Parsed arguments: {'city': 'Tokyo'}

=== Executing local tool ===
Function: get_weather
Arguments: {'city': 'Tokyo'}

=== Tool result ===
{
  "city": "Tokyo",
  "temperature_c": 28,
  "condition": "Sunny"
}

=== Final parsed answer ===
Tokyo is currently sunny with a temperature of 28°C.
```

Generated wording and tool call IDs may vary between runs.

## Important behavior

Tool calling should not be confused with direct function execution by the model.

Hy3 returns a structured request such as:

```text
Call get_weather with city="Tokyo"
```

The client application is responsible for:

1. validating the requested tool name
2. parsing the arguments
3. executing trusted application code
4. collecting the result
5. returning the result to the model

In production systems, never execute arbitrary model-generated function names or arguments without validation.

## What this example demonstrates

This example shows:

1. how to define tools with JSON Schema
2. how to inspect `message.tool_calls`
3. how to parse JSON function arguments
4. how to execute a local Python function
5. how to preserve the assistant tool-call message
6. how to return a result with `role="tool"`
7. how to associate results with `tool_call_id`
8. how to complete a multi-turn tool execution loop
