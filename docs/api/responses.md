# Hy3 Responses API

This guide explains how to call Hy3 through the Tencent Cloud TokenHub Responses API and how it differs from the [Chat Completions API](../../quickstart.md).

Responses API uses a unified `input` and `output` model. Messages, reasoning items, function calls, and function-call results are represented as typed Items. This is useful for tool calling, multimodal input, and more complex Agent workflows.

## Chat Completions and Responses: quick comparison

| Topic              | Chat Completions API            | Responses API                                                                                |
|--------------------|---------------------------------|----------------------------------------------------------------------------------------------|
| Endpoint           | `/v1/chat/completions`          | `/v1/responses`                                                                              |
| Input              | `messages` array                | Top-level `input`, either a string or an Item array                                          |
| Instructions       | Usually a `system` message      | Optional top-level `instructions`                                                            |
| Text output        | `choices[0].message.content`    | Usually `response.output_text`                                                               |
| Output structure   | `choices`                       | `output` Item array containing `message`, `reasoning`, or `function_call` Items              |
| Tool calling       | `tool_calls` and `role: "tool"` | `function_call` and `function_call_output` Items linked by `call_id`                         |
| Conversation state | Resend `messages` history       | Resend input Items; `previous_response_id` is not reliable in the current compatibility path |

Migration is not only a URL change. Input mapping, response parsing, tool calls, structured output, and streaming events all need to be updated. For ordinary text, the most common mapping is:

```text
choices[0].message.content  →  response.output_text
```

## 1. Basic information

### Endpoint

Guangzhou:

```text
https://tokenhub.tencentmaas.com/v1/responses
```

Singapore:

```text
https://tokenhub-intl.tencentmaas.com/v1/responses
```

The API key, Base URL, and service region must match. Authentication uses the same header as Chat Completions:

```http
Authorization: Bearer ${HY3_API_KEY}
```

### Model name

This guide uses the Hy3 service ID:

```text
hy3
```

The model marketplace declares Hy3 support for OpenAI Chat Completions, OpenAI Responses, and Anthropic Messages. The model list in the generic Responses compatibility document describes the models explicitly listed for that compatibility path and should not replace the model marketplace declaration. Before using another model, verify its model ID and protocol support with the console or `GET /v1/models`.

## 2. First request

Use top-level `instructions` for high-level behavior and `input` for the user request:

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "instructions": "You are a helpful assistant.",
    "input": "Hello",
    "stream": false
  }'
```

### Request fields

| Field          | Type            | Description                                                  |
|----------------|-----------------|--------------------------------------------------------------|
| `model`        | string          | Model or service ID, such as `hy3`.                          |
| `instructions` | string or array | High-level instructions for the current response.            |
| `input`        | string or array | User input, either plain text or input Items.                |
| `stream`       | boolean         | Whether to return SSE events instead of a complete response. |

`instructions` applies only to the current request. If conversation history is manually provided in `input`, include the required instructions explicitly.

### Roles and instructions

Stable behavior instructions are best placed in `instructions`. They can also be represented as a `developer` message in an `input` array:

```json
{
  "model": "hy3",
  "input": [
    {"role": "developer", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello"}
  ],
  "stream": false
}
```

### Response structure

A typical response contains:

```json
{
  "id": "30d23e89-48b8-4ea2-8ba3-b52db746d4c8",
  "object": "response",
  "model": "hy3",
  "status": "completed",
  "output": [
    {
      "type": "message",
      "role": "assistant",
      "content": [
        {"type": "output_text", "text": "Hello! How can I help you?"}
      ]
    }
  ],
  "output_text": "Hello! How can I help you?",
  "usage": {
    "input_tokens": 22,
    "output_tokens": 12,
    "total_tokens": 34
  },
  "error": null
}
```

For ordinary text, read `output_text`. If the application handles tools, reasoning, or other Item types, iterate through `output` and branch on each Item's `type`.

## 3. Python OpenAI SDK

Install the dependencies from the repository:

```bash
uv sync
```

The minimal example is [`examples/06_responses_basic.py`](../../examples/06_responses_basic.py):

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["HY3_API_KEY"],
    base_url="https://tokenhub.tencentmaas.com/v1",
)

response = client.responses.create(
    model="hy3",
    instructions="You are a helpful assistant.",
    input="Hello",
)

print(response.output_text)
```

## 4. Multi-turn conversations

In the current TokenHub compatibility path, the safest approach is to store the history in the client and resend it through `input`:

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": [
      {"role": "user", "content": "Hello, my name is Xiao Ming."},
      {"role": "assistant", "content": "Hello, Xiao Ming!"},
      {"role": "user", "content": "What is my name?"}
    ],
    "stream": false
  }'
```

The field `previous_response_id` can be accepted by the endpoint while still failing to restore the previous context on the current service path. The field name itself is valid, but applications should not rely on it without verifying the behavior. Use explicit history in `input` when context continuity is required.

## 5. Reasoning mode

Responses API uses `reasoning.effort` rather than the Chat Completions `thinking` style:

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "Calculate 37 × 24 and explain the result in one sentence.",
    "reasoning": {"effort": "high"},
    "stream": false
  }'
```

A reasoning-enabled response may contain a `reasoning` Item and a final `message` Item. The `usage.output_tokens_details.reasoning_tokens` field can be used to identify reasoning-token usage. Do not assume that the service will return or that an application should display the model's private chain of thought.

The available effort values and behavior depend on the model and service. See [`examples/05_reasoning_mode.py`](../../examples/05_reasoning_mode.py) for a Chat Completions comparison and the [TokenHub reasoning guide](https://cloud.tencent.com/document/product/1823/131208).

## 6. Tool calling

Responses function calling has four stages: declare a tool, parse the `function_call`, execute the local function, and return a `function_call_output` Item. The model does not execute the local function.

### 6.1 Declare a function

Responses tool definitions use a flat structure. `type`, `name`, `description`, and `parameters` are direct fields of the tool object:

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "What is the weather in Shenzhen?",
    "tools": [
      {
        "type": "function",
        "name": "get_weather",
        "description": "Get current weather information for a city",
        "parameters": {
          "type": "object",
          "properties": {
            "city": {"type": "string", "description": "City name"}
          },
          "required": ["city"],
          "additionalProperties": false
        }
      }
    ],
    "tool_choice": "auto",
    "stream": false
  }'
```

`properties` defines the available arguments, `required` lists mandatory arguments, and `additionalProperties: false` rejects undeclared fields. `tool_choice: "auto"` lets the model decide whether to call the tool.

### 6.2 Parse a function call

The first response may contain:

```json
{
  "type": "function_call",
  "id": "fc_example",
  "status": "completed",
  "name": "get_weather",
  "call_id": "chatcmpl-tool-example",
  "arguments": "{\"city\": \"Shenzhen\"}"
}
```

Parse `arguments` as a JSON string and execute the function named by `name`. The returned `call_id` is the correlation ID for the next request.

### 6.3 Return the tool result

Include the previous function-call Item and a `function_call_output` Item in the next `input` array:

```json
{
  "type": "function_call_output",
  "call_id": "chatcmpl-tool-example",
  "output": "{\"city\":\"Shenzhen\",\"weather\":\"sunny\",\"temperature\":28}"
}
```

`function_call_output.call_id` must exactly match the previous `function_call.call_id`. The `output` value is normally a JSON string. Repeat the process if the next response contains another function call. See [`examples/08_responses_tool_calling.py`](../../examples/08_responses_tool_calling.py) for a complete runnable flow.

## 7. Streaming output

Set `stream` to `true` to receive Server-Sent Events:

```bash
curl -N -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "Hello",
    "stream": true
  }'
```

Common events include:

| Event | Description |
| --- | --- |
| `response.created` | Response object created. |
| `response.in_progress` | Response generation is in progress. |
| `response.output_item.added` | A new output Item was added. |
| `response.output_text.delta` | A text increment; append `delta` in order. |
| `response.output_text.done` | The current text output is complete. |
| `response.output_item.done` | The current output Item is complete. |
| `response.completed` | The entire response is complete and usually contains `usage`. |
| `response.failed` | The response failed and contains error information. |

Not every event contains `delta`. Check the event type before reading event-specific fields. Do not reuse a Chat Completions chunk parser for Responses events.

The current TokenHub response may contain `output: null` in `response.created`, which causes some OpenAI SDK high-level Responses stream parsers to fail when they assume `output` is always an array. [`examples/07_responses_streaming.py`](../../examples/07_responses_streaming.py) therefore parses the raw SSE stream with the Python standard library.

## 8. Structured output

Use `text.format` and `json_schema` to constrain the output:

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "Extract the person information: Zhang San, male, 25, from Beijing.",
    "text": {
      "format": {
        "type": "json_schema",
        "name": "person_info",
        "schema": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "gender": {"type": "string"},
            "age": {"type": "number"},
            "city": {"type": "string"}
          },
          "required": ["name", "gender", "age", "city"],
          "additionalProperties": false
        },
        "strict": true
      }
    },
    "stream": false
  }'
```

The response still uses a normal `message` Item, but its `output_text` value is a JSON string:

```json
{
  "age": 25,
  "city": "Beijing",
  "gender": "male",
  "name": "Zhang San"
}
```

Parse it once more in the application:

```python
import json

person = json.loads(response.output_text)
print(person["name"])
```

`output_text` is not already a Python dictionary or JavaScript object. Handle empty responses, failed requests, and JSON parsing errors in production. See [`examples/09_responses_structured_output.py`](../../examples/09_responses_structured_output.py).

## 9. Request parameters

The following parameters are commonly used by the current compatibility path:

| Parameter | Type | Description |
| --- | --- | --- |
| `temperature` | number | Controls sampling randomness. The documented range is `[0, 2]`. |
| `top_p` | number | Nucleus sampling parameter. The documented range is `[0, 1]`. |
| `max_output_tokens` | integer | Maximum generated output tokens. It must be greater than zero. |
| `tools` | array | Function tools; the current compatibility path supports `function` tools. |
| `tool_choice` | string or object | Tool selection policy. |
| `reasoning.effort` | string | Reasoning effort, when supported by the model. |
| `text.format` | object | Text, JSON object, or JSON Schema output format. |
| `stream` | boolean | Complete response or SSE stream. |

### `stop` behavior

The compatibility documentation does not list `stop` as a fully supported Responses parameter. A test request returned HTTP `200`, but the output still contained `STOP`:

```bash
curl -i -X POST "https://tokenhub.tencentmaas.com/v1/responses" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "input": "Output the following and end with STOP: first line, second line.",
    "stop": ["STOP"],
    "stream": false
  }'
```

The observed output was `first line\nsecond line\nSTOP` in the real test. This indicates that the service accepted the field but did not apply the expected truncation. Do not rely on `stop` for Responses output control without retesting the exact model and service path. Prefer structured output or client-side post-processing when strict output control is required.

## 10. Common errors

Responses API errors usually use this structure:

```json
{
  "error": {
    "type": "rate_limit_error",
    "code": "429006",
    "message": "The model service is currently busy or has reached its serving capacity limit. Please reduce the request frequency and try again later.",
    "message_zh": "当前模型服务繁忙或已达服务容量上限，请降低请求频率后稍后重试。",
    "source": "gateway",
    "request_id": "57b8d6ff-03dd-45a0-8d8e-5eebba3e0470"
  }
}
```

Read `error.code`, `error.type`, `error.message_zh`, and `error.request_id` first. Lower request frequency, wait before retrying, and use exponential backoff with random jitter for transient errors. If `Retry-After` is present, follow it before retrying. Record the request ID, request time, and model name when reporting persistent failures. See [`examples/10_error_handling_retry.py`](../../examples/10_error_handling_retry.py) and [TokenHub API error codes](https://cloud.tencent.com/document/product/1823/131595).

## 11. Notes

- Responses output Items are not identical to Chat Completions `choices`; do not reuse the old parser without adapting it.
- Use `response.output_text` for ordinary text and iterate over `response.output` for tools, reasoning, and other Item types.
- Do not put API keys in Python files, shell scripts, Markdown examples, or committed `.env` files.
- Verify parameter support against the model marketplace, TokenHub documentation, and an actual response. A field may be accepted but have no effect.

## References

- [TokenHub Responses API compatibility](https://cloud.tencent.com/document/product/1823/133813): parameter support, input/output structures, and compatibility limits.
- [TokenHub language-model overview](https://cloud.tencent.com/document/product/1823/130079): common parameters, response fields, tools, and streaming.
- [TokenHub API usage](https://cloud.tencent.com/document/product/1823/130078): endpoints, authentication, model listing, and exceptions.
- [Hy3 calling guide](https://cloud.tencent.com/document/product/1823/132252): Hy3 limits, protocol support, and model-specific usage.
- [TokenHub reasoning guide](https://cloud.tencent.com/document/product/1823/131208): `thinking`, `reasoning_effort`, and reasoning behavior.
- [TokenHub API error codes](https://cloud.tencent.com/document/product/1823/131595): HTTP status codes and business errors.
