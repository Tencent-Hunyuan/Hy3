<p align="left">
    English ｜ <a href="quickstart_cn.md">中文</a>
</p>

# Hy3 API Quickstart

This guide shows how to call the Tencent Cloud TokenHub hosted Hy3 API. Local deployment of the Hy3 model is not required.

The guide uses the Chat Completions API for the first request and then introduces the main capabilities. For a separate Responses API guide, see [Responses API](docs/api/responses.md).

## 1. Create an API key

Create an API key in the [TokenHub API Key console](https://console.cloud.tencent.com/tokenhub/apikey).

Do not write a real key directly into source code, documentation, screenshots, or Git. Store it in an environment variable instead:

```bash
export HY3_API_KEY="YOUR_TOKENHUB_API_KEY"
```

If a key has been exposed, disable or delete it in the console and create a new one.

## 2. Choose an API protocol

Hy3 supports the following TokenHub-compatible protocols:

- Chat Completions API: the default protocol in this guide, suitable for ordinary chat, streaming, and function calling.
- Responses API: a unified output model for messages, reasoning, tools, and more complex Agent workflows. See [Responses API](docs/api/responses.md).
- Anthropic Messages API: available according to the model and service support matrix.

This guide focuses on Chat Completions. The [Responses API guide](docs/api/responses.md) documents its different request and response structures.

## 3. Basic information

### Base URL

The API key, service region, and Base URL must belong to the same region.

| Region | Base URL | Scope |
| --- | --- | --- |
| Guangzhou | `https://tokenhub.tencentmaas.com/v1` | Mainland China |
| Singapore | `https://tokenhub-intl.tencentmaas.com/v1` | Global |

The platform also provides backup domains. Use them only when the default domain is unavailable:

- Guangzhou: `https://tokenhub.tencentmaas.cn/v1`
- Singapore: `https://tokenhub-intl.tencentmaas.cn/v1`

### API key

Pass the API key in the `Authorization` header:

```http
Authorization: Bearer ${HY3_API_KEY}
```

The available model IDs can be checked with:

```bash
curl "https://tokenhub.tencentmaas.com/v1/models" \
  -H "Authorization: Bearer ${HY3_API_KEY}"
```

### Model name

The Hy3 service ID is:

```text
hy3
```

Use the service ID in the `model` field rather than a local checkpoint path. Hy3 supports TokenHub's OpenAI Chat Completions, OpenAI Responses, and Anthropic protocols; this guide uses Chat Completions by default.

### Model and throughput limits

The following Hy3 service information was recorded from the [model marketplace](https://console.cloud.tencent.com/tokenhub/models/detail?modelId=hy3&regionId=1&from=all&Is=sdk-topnav) on July 22, 2026:

| Limit | Value | Description |
| --- | ---: | --- |
| Maximum input tokens | 192k | Maximum input length for a single request. |
| Maximum output tokens | 128k | Maximum output length; reasoning tokens count toward this limit. |
| Context window | 256k | Combined input and output context limit. |
| Maximum TPM | 1,000,000 | Maximum input and output tokens processed per minute. |
| Maximum RPM | 60 | Maximum requests per minute. |

The first three values are model capacity limits. TPM and RPM are service throttling limits and may vary by region, plan, API key, or account. Always check the latest value in the model marketplace before production use.

## 4. First request

The Chat Completions request consists of a URL, request headers, and a JSON body:

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello"}
    ],
    "stream": false
  }'
```

### Request fields

| Field | Type | Description |
| --- | --- | --- |
| `model` | string | Model or service ID. Use `hy3` for Hy3. |
| `messages` | array | Ordered conversation messages. |
| `messages[].role` | string | Message role, such as `system`, `user`, `assistant`, or `tool`. |
| `messages[].content` | string or array | Message text or supported content blocks. |
| `stream` | boolean | Whether to return an SSE stream. `false` returns a complete response. |

### Response example

Responses usually contain the following structure:

```json
{
  "id": "c27d9b74-497e-4968-8138-530063de4f40",
  "object": "chat.completion",
  "model": "hy3",
  "created": 1784381073,
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 22,
    "completion_tokens": 15,
    "total_tokens": 37
  }
}
```

For ordinary text, read `choices[0].message.content`. `finish_reason: "stop"` normally indicates that the model completed the answer normally.

### Python OpenAI SDK

Install the SDK:

```bash
uv sync
```

The minimal example is [`examples/01_basic_chat.py`](examples/01_basic_chat.py). Run it from the repository root:

```bash
uv run --env-file .env python examples/01_basic_chat.py
```

The script creates an OpenAI-compatible client with the TokenHub Base URL and reads `response.choices[0].message.content`.

## 5. Multi-turn conversations

Pass the conversation history in `messages` in chronological order. The current request should normally end with a `user` message:

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hello! How can I help?"},
      {"role": "user", "content": "What is 37 × 24?"}
    ],
    "stream": false
  }'
```

The client is responsible for storing and resending the conversation history. If a previous response contains reasoning-related fields, whether those fields must be preserved depends on the model and TokenHub protocol support.

## 6. Streaming output

Set `stream` to `true` to receive Server-Sent Events (SSE):

```bash
curl -N -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "Introduce Shenzhen in three sentences."}],
    "stream": true
  }'
```

Typical events look like this:

```text
data: {"choices":[{"index":0,"delta":{"role":"assistant"}}]}
data: {"choices":[{"index":0,"delta":{"content":"Shenzhen"}}]}
data: {"choices":[{"index":0,"delta":{"content":" is a modern city."},"finish_reason":"stop"}]}
data: [DONE]
```

The client should concatenate `delta.content` in order. Not every chunk contains text, so check that `choices` and `delta.content` are present before reading them. `data: [DONE]` is a stream terminator, not a JSON object.

To receive usage in the final chunk, add:

```json
"stream_options": {"include_usage": true}
```

The final usage chunk may contain an empty `choices` array. See [`examples/02_streaming.py`](examples/02_streaming.py) and [`examples/03_streaming_vs_non_streaming.py`](examples/03_streaming_vs_non_streaming.py).

## 7. Reasoning mode

Reasoning parameters are defined by the TokenHub service and may vary by protocol and model. Do not copy local vLLM or SGLang `chat_template_kwargs` settings into a hosted API request without checking the corresponding TokenHub documentation.

For Chat Completions, the commonly used parameters are:

```json
"thinking": {"type": "enabled"}
```

Some services also expose:

```json
"reasoning_effort": "high"
```

Whether either field is accepted and effective depends on the model and service version. The example [`examples/05_reasoning_mode.py`](examples/05_reasoning_mode.py) compares normal and reasoning requests.

Applications should not display the model's private chain of thought by default. Use the final answer and usage fields required by the application.

### Interleaved thinking

[Interleaved thinking](https://cloud.tencent.com/document/product/1823/130930) combines reasoning and tool calls. The request still uses the supported thinking, reasoning, and tools fields, but the model may call tools multiple times. The application must process each tool call until the model returns a final answer.

## 8. Tool calling

Tool calling usually consists of two model requests and one local function execution:

1. Declare callable functions in `tools`.
2. Parse `tool_calls` when the model requests a tool and execute the local function.
3. Send the result back as a `role: "tool"` message so the model can produce the final answer.

The model does not execute local functions. Function execution, permissions, validation, and error handling belong to the application.

### First request: declare a tool

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "What is the weather in Shenzhen?"}],
    "tools": [
      {
        "type": "function",
        "function": {
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
      }
    ],
    "tool_choice": "auto",
    "stream": false
  }'
```

`tools` is an array of function definitions. `function.name` selects the application function, `description` helps the model decide when to use it, and `function.parameters` is a JSON Schema. `tool_choice: "auto"` lets the model decide whether to call a tool.

### Model tool call

The model may return a message like:

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "chatcmpl-tool-example",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"city\":\"Shenzhen\"}"
      }
    }
  ]
}
```

Parse `function.arguments` as a JSON string. The tool call ID must be returned as `tool_call_id`:

```json
{
  "role": "tool",
  "tool_call_id": "chatcmpl-tool-example",
  "content": "{\"city\":\"Shenzhen\",\"weather\":\"sunny\",\"temperature\":28}"
}
```

The second request contains the original conversation, the assistant tool-call message, and the tool result. See [`examples/04_tool_calling.py`](examples/04_tool_calling.py) for a complete loop that supports multiple tool calls.

## 9. Structured output

Use `response_format` to request a JSON Schema-constrained answer:

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "Extract the person information: Zhang San, 35, senior software engineer, skilled in Python, Java, and machine learning."}
    ],
    "response_format": {
      "type": "json_schema",
      "json_schema": {
        "name": "person_info",
        "schema": {
          "type": "object",
          "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "occupation": {"type": "string"},
            "skills": {"type": "array", "items": {"type": "string"}}
          },
          "required": ["name", "age", "occupation", "skills"]
        }
      }
    },
    "stream": false
  }'
```

The structured result is still returned as a string in `choices[0].message.content`. Parse it a second time in the application:

```python
import json

person = json.loads(response.choices[0].message.content)
print(person["name"])
```

The example response contains fields such as `name`, `age`, `occupation`, and `skills`. See [`examples/09_responses_structured_output.py`](examples/09_responses_structured_output.py) for a complete Python example.

## 10. Common request parameters

The following optional parameters are commonly used at the top level of a Chat Completions request:

| Parameter | Type | Description |
| --- | --- | --- |
| `temperature` | number | Controls randomness. Lower values are usually more stable; higher values are more diverse. |
| `top_p` | number | Nucleus sampling threshold. Usually adjust `temperature` or `top_p`, rather than both aggressively. |
| `max_tokens` | integer | Maximum number of generated output tokens for Chat Completions. Check the model limit. |
| `stop` | string or string array | Stops generation when a specified sequence is reached. |
| `tools` | array | Declares callable tools. |
| `tool_choice` | string or object | Controls tool selection, such as `auto`. |
| `stream` | boolean | Selects complete or SSE streaming output. |

### `temperature`

Controls sampling randomness. When the same prompt is sent repeatedly, a lower value usually produces more similar answers. Start with a small value such as `0.2` or `0.3` when stable output is important.

### `top_p`

Controls the cumulative probability mass considered for the next token. Lower values usually narrow the candidate set. The supported range is typically `[0, 1]`.

### `max_tokens`

Limits the generated output length. It does not guarantee that the model will finish the requested task within the limit. Reasoning tokens may also count toward the output limit depending on the service.

### `stop`

`stop` is a signal that tells the model to stop when it generates a specified marker; it is not a request to output that marker. For Chat Completions, the following test returned HTTP `200`, omitted `STOP` from the content, and returned `finish_reason: "stop"`:

```bash
curl -i -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "Output the following and end with STOP: first line, second line."}],
    "stop": ["STOP"],
    "stream": false
  }'
```

The observed content was `first line\nsecond line\n`, without `STOP`. In contrast, the current Hy3 Responses API test accepted the field but did not truncate the output, so applications should verify the behavior separately for each protocol.

## 11. Common errors and troubleshooting

Errors usually have this structure:

```json
{
  "error": {
    "message": "English error description",
    "message_zh": "Chinese error description",
    "code": "Business error code",
    "type": "Error type",
    "source": "client | gateway | upstream",
    "request_id": "Unique request ID"
  }
}
```

Important fields:

| Field | Description |
| --- | --- |
| `error.message` | English description, useful for logs. |
| `error.message_zh` | Chinese description, suitable for Chinese user-facing messages. |
| `error.code` | TokenHub business error code. It may be a string or an integer. |
| `error.type` | Error category, such as a parameter or rate-limit error. |
| `error.source` | Error source: `client`, `gateway`, or `upstream`. |
| `error.request_id` | Unique request ID for support and troubleshooting. |

Common HTTP status codes include:

| Status | Typical cause | Suggested action |
| --- | --- | --- |
| `400` | Invalid body, missing field, or invalid parameter. | Check `model`, `messages`, and parameter ranges. |
| `401` | Missing, invalid, expired, or disabled API key. | Check the Authorization header and key status. |
| `403` | Insufficient plan, model, account, IP, or tool permission. | Check service permissions. |
| `413` | Request body is too large. | Reduce messages, tools, or other input. |
| `429` | RPM, TPM, TPD, concurrency, or capacity limit. | Reduce frequency or concurrency and retry later. |
| `451` | Content safety policy triggered. | Adjust the input or output request. |
| `500`–`504` | Platform, upstream, or gateway failure. | Retry and provide `request_id` if the problem persists. |

### Model service busy: `429006`

The gateway may return this error when the model service is busy or has reached its serving capacity:

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

Lower the request rate, wait before retrying, and use exponential backoff with random jitter. If the response includes `Retry-After`, wait for that duration first. Record the request ID, time, and model name if the error persists. This error normally indicates service capacity rather than invalid JSON; changing `messages` or `response_format` does not directly resolve it. See [`examples/10_error_handling_retry.py`](examples/10_error_handling_retry.py).

For the complete error-code list, see [TokenHub API error codes](https://cloud.tencent.com/document/product/1823/131595).

## 12. Examples and further reading

The curl snippets above explain the protocol format. For complete runnable Python examples, read [`examples/README.md`](examples/README.md). Every script has a matching Chinese Markdown description with its run command, parsing logic, and an observed output example.

| Scenario | Example |
| --- | --- |
| Basic chat | [`01_basic_chat.py`](examples/01_basic_chat.py) |
| Streaming | [`02_streaming.py`](examples/02_streaming.py) |
| Streaming comparison | [`03_streaming_vs_non_streaming.py`](examples/03_streaming_vs_non_streaming.py) |
| Chat tool calling | [`04_tool_calling.py`](examples/04_tool_calling.py) |
| Chat reasoning | [`05_reasoning_mode.py`](examples/05_reasoning_mode.py) |
| Responses basic call | [`06_responses_basic.py`](examples/06_responses_basic.py) |
| Responses streaming | [`07_responses_streaming.py`](examples/07_responses_streaming.py) |
| Responses tool calling | [`08_responses_tool_calling.py`](examples/08_responses_tool_calling.py) |
| Responses structured output | [`09_responses_structured_output.py`](examples/09_responses_structured_output.py) |
| Error handling and retry | [`10_error_handling_retry.py`](examples/10_error_handling_retry.py) |

Run an example from the repository root:

```bash
uv run --env-file .env python examples/01_basic_chat.py
```

## 13. Reference documentation

- [TokenHub Quickstart](https://cloud.tencent.com/document/product/1823/130058): TokenHub console and basic setup.
- [TokenHub API usage](https://cloud.tencent.com/document/product/1823/130078): endpoints, authentication, model listing, and exceptions.
- [TokenHub language-model overview](https://cloud.tencent.com/document/product/1823/130079): common parameters, response fields, tools, and streaming.
- [Hy3 calling guide](https://cloud.tencent.com/document/product/1823/132252): Hy3 limits, protocol support, and model-specific usage.
- [TokenHub reasoning](https://cloud.tencent.com/document/product/1823/131208): `thinking`, `reasoning_effort`, and reasoning-related behavior.
- [TokenHub API error codes](https://cloud.tencent.com/document/product/1823/131595): HTTP status codes, business errors, and troubleshooting.
- [TokenHub Responses API compatibility](https://cloud.tencent.com/document/product/1823/133813): Responses parameters, input/output structures, and compatibility limits.
- [TokenHub glossary](https://cloud.tencent.com/document/product/1823/130120#2897): Common TokenHub terminology.

Do not infer parameter support from a single response. When changing the model, region, or protocol, verify the behavior again against the model marketplace, official documentation, and an actual API response.
