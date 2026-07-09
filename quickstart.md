# Hy3 API Quickstart

This guide shows how to call Hy3 through an OpenAI-compatible Chat Completions API. It is designed for a local or self-hosted endpoint first, and the examples can also be adapted to any gateway that exposes the same API shape.

## Prerequisites

- Python 3.8 or newer.
- A running Hy3 OpenAI-compatible API server.
- The OpenAI Python SDK:

```bash
pip install -r examples/requirements.txt
```

## API Basics

| Item | Default |
| --- | --- |
| Base URL | `http://127.0.0.1:8000/v1` |
| API key | `EMPTY` for local/self-hosted deployments |
| Model | `hy3` |
| API style | OpenAI-compatible Chat Completions API |
| Python SDK | `openai>=1.0.0` |

All example scripts read these environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | API server base URL |
| `HY3_API_KEY` | `EMPTY` | API key passed as bearer token |
| `HY3_MODEL` | `hy3` | Model name exposed by the server |

Windows PowerShell:

```powershell
$env:HY3_BASE_URL = "http://127.0.0.1:8000/v1"
$env:HY3_API_KEY = "EMPTY"
$env:HY3_MODEL = "hy3"
```

macOS / Linux:

```bash
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
```

If your deployment uses a real key or a different model alias, replace these values locally. Do not commit real API keys.

## 5-minute First Call

### curl

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {
        "role": "user",
        "content": "Hello! Can you briefly introduce yourself?"
      }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "extra_body": {
      "chat_template_kwargs": {
        "reasoning_effort": "no_think"
      }
    }
  }'
```

The assistant text is returned at:

```text
response.choices[0].message.content
```

Example output:

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Hello! I am Hy3, a language model that can help with questions, writing, coding, and reasoning tasks."
      }
    }
  ]
}
```

### Python SDK

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
)

response = client.chat.completions.create(
    model=os.getenv("HY3_MODEL", "hy3"),
    messages=[
        {"role": "user", "content": "Give me three practical API client tips."}
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

print(response.choices[0].message.content)
```

## Multi-turn Chat

Keep prior messages in the `messages` list. Add the assistant answer back into the history before asking the next user question:

```python
messages = [
    {"role": "system", "content": "You are a concise developer assistant."},
    {"role": "user", "content": "Explain what an API timeout is in one sentence."},
]

first = client.chat.completions.create(model="hy3", messages=messages)
answer = first.choices[0].message.content

messages.append({"role": "assistant", "content": answer})
messages.append({"role": "user", "content": "Now give me one Python mitigation."})

second = client.chat.completions.create(model="hy3", messages=messages)
print(second.choices[0].message.content)
```

See [examples/01_basic_chat.md](examples/01_basic_chat.md).

## Streaming

Set `stream=True` to receive incremental chunks:

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Write a short API test checklist."}],
    max_tokens=256,
    stream=True,
)

for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    if delta and delta.content:
        print(delta.content, end="", flush=True)
```

Streaming response parsing uses:

```text
chunk.choices[0].delta.content
```

See [examples/02_streaming.md](examples/02_streaming.md) and [examples/03_streaming_vs_non_streaming.md](examples/03_streaming_vs_non_streaming.md).

## Parameters

| Parameter | Example | Description |
| --- | --- | --- |
| `model` | `"hy3"` | Model name exposed by your Hy3 server |
| `messages` | `[{"role": "user", "content": "..."}]` | Chat history in OpenAI format |
| `temperature` | `0.9` | Higher values make output more diverse |
| `top_p` | `1.0` | Nucleus sampling threshold |
| `max_tokens` | `256` | Maximum generated tokens for the answer |
| `stop` | `["\n\nUser:"]` | Optional stop sequence list |
| `stream` | `True` | Return incremental chunks instead of one full response |
| `tools` | See tool calling example | Function schemas the model may request |
| `tool_choice` | `"auto"` | Let the model decide whether to call tools |
| `extra_body.chat_template_kwargs.reasoning_effort` | `"no_think"` / `"high"` | Hy3 reasoning mode switch |

## Reasoning Mode

Hy3 examples pass reasoning mode through `extra_body`:

```python
extra_body={
    "chat_template_kwargs": {
        "reasoning_effort": "no_think"
    }
}
```

Use `no_think` for fast direct answers. Use a stronger mode such as `high` for math, logic, multi-step reasoning, or code analysis if your serving template supports it. See [examples/05_reasoning_mode.md](examples/05_reasoning_mode.md).

## Tool Calling

Tool calling has three steps:

1. Send user messages plus `tools` schemas.
2. Read `response.choices[0].message.tool_calls` and execute the requested local functions.
3. Append each result as a `role="tool"` message and call the model again.

The final answer is still read from:

```python
final_response.choices[0].message.content
```

See [examples/04_tool_calling.md](examples/04_tool_calling.md).

## Rate Limits

Hy3 itself does not define a public fixed API rate limit in this repository. For self-hosted deployments, throughput and concurrency depend on GPU memory, parallelism, max model length, server configuration, and gateway-level throttling.

If your serving layer returns HTTP `429` or the SDK raises `RateLimitError`, reduce concurrency and retry with exponential backoff. See [examples/06_error_handling_retry.md](examples/06_error_handling_retry.md).

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `401 Unauthorized` | API key is missing, invalid, or expired | Check `HY3_API_KEY` |
| `404 model not found` | `HY3_MODEL` does not match the served model name | Set the model alias exposed by your server |
| Connection refused | API server is not running or `HY3_BASE_URL` is wrong | Start the server and check the `/v1` base URL |
| `RateLimitError` / `429` | Too many requests or gateway throttling | Lower concurrency and use retry with backoff |
| `APITimeoutError` | Generation exceeded client timeout | Increase timeout, reduce `max_tokens`, or stream |
| Empty streaming output | The client is reading `message.content` instead of `delta.content` | Parse each stream chunk |
| Tool answer missing | Tool result was not appended with `role="tool"` and `tool_call_id` | Follow the tool calling loop |

## Examples

| Example | Capability |
| --- | --- |
| [01_basic_chat.md](examples/01_basic_chat.md) | Single-turn and multi-turn chat |
| [02_streaming.md](examples/02_streaming.md) | Streaming request and chunk parsing |
| [03_streaming_vs_non_streaming.md](examples/03_streaming_vs_non_streaming.md) | First-token latency and total latency |
| [04_tool_calling.md](examples/04_tool_calling.md) | Tool call execution and tool result loop |
| [05_reasoning_mode.md](examples/05_reasoning_mode.md) | Reasoning mode on/off comparison |
| [06_error_handling_retry.md](examples/06_error_handling_retry.md) | Timeout, rate limit, and network retry handling |

Run any script directly:

```bash
python examples/01_basic_chat.py
```
