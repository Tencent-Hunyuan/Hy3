<p align="left">
    <a href="./quickstart_CN.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Hy3 API Quickstart

This guide helps developers run the first Hy3 API call in about 5 minutes and learn the main API patterns in about 30 minutes.

> This document assumes you already have a Hy3 OpenAI-compatible API server running through vLLM or SGLang. If you are self-hosting, start the server first and then run the examples below.

## 1. Basic information

| Item | Default | Description |
| --- | --- | --- |
| Base URL | `http://127.0.0.1:8000/v1` | OpenAI-compatible API root. Change it if your server listens on another host or port. |
| Chat endpoint | `/chat/completions` | Full URL: `${HY3_BASE_URL}/chat/completions`. |
| API key | `EMPTY` | Local/self-hosted servers often accept a dummy key. If your gateway sets an auth token, use that token instead. |
| Model name | `hy3` | Should match the server-side `--served-model-name hy3`. |
| Recommended sampling | `temperature=0.9`, `top_p=1.0` | Good default for general chat and coding tasks. |
| Context length | up to `256K` tokens | Actual usable length also depends on server configuration and available memory. |
| Rate limit | deployment-specific | Hy3 itself is self-hosted in this guide. Rate limits come from your serving gateway, reverse proxy, queue, or GPU capacity. Treat HTTP `429` as rate limiting and retry with exponential backoff. |

## 2. Install client dependencies

```bash
python -m pip install -U openai
```

Set environment variables:

```bash
export HY3_BASE_URL="${HY3_BASE_URL:-http://127.0.0.1:8000/v1}"
export HY3_API_KEY="${HY3_API_KEY:-EMPTY}"
export HY3_MODEL="${HY3_MODEL:-hy3}"
```

Optional health checks:

```bash
curl "${HY3_BASE_URL}/models" \
  -H "Authorization: Bearer ${HY3_API_KEY}"

curl "${HY3_BASE_URL}/health" || true
```

## 3. Minimal runnable example: curl

```bash
curl "${HY3_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "Hello! Can you briefly introduce yourself?"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "chat_template_kwargs": {
      "reasoning_effort": "no_think"
    }
  }'
```

Expected response shape:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1760000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I am Hy3..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 16,
    "completion_tokens": 50,
    "total_tokens": 66
  }
}
```

## 4. Minimal runnable example: Python OpenAI SDK

Create `hello_hy3.py`:

```python
import os
from openai import OpenAI

BASE_URL = os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.getenv("HY3_API_KEY", "EMPTY")
MODEL = os.getenv("HY3_MODEL", "hy3")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=60.0)

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "user", "content": "Hello! Can you briefly introduce yourself?"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

message = response.choices[0].message
print(message.content)
print("usage:", response.usage)
```

Run:

```bash
python hello_hy3.py
```

## 5. Parameter reference

| Parameter | Type | Example | Notes |
| --- | --- | --- | --- |
| `model` | string | `"hy3"` | Must match the served model name. |
| `messages` | array | `[{"role":"user","content":"..."}]` | Chat history. Use `system`, `user`, `assistant`, and `tool` roles as needed. |
| `temperature` | number | `0.9` | Higher values increase randomness. Use `0` or a small value for deterministic tasks. |
| `top_p` | number | `1.0` | Nucleus sampling. Usually tune either `temperature` or `top_p`, not both aggressively. |
| `max_tokens` | integer | `512` | Maximum generated tokens. Lower it to reduce latency and memory pressure. |
| `stop` | string/array | `["\nObservation:"]` | Stop generation when a stop sequence appears. |
| `stream` | boolean | `true` | If `true`, returns chunks as soon as tokens are generated. Useful for UI and lower perceived latency. |
| `tools` | array | OpenAI function schema | Defines functions the model may call. The application must execute the function and send tool results back. |
| `tool_choice` | string/object | `"auto"`, `"none"`, `"required"` | Use `auto` for normal tool calling, `none` to disable tools, or a named function to force a specific tool. |
| `parallel_tool_calls` | boolean | `false` | Set to `false` if your tool loop expects at most one tool call per assistant message. |
| `extra_body.chat_template_kwargs.reasoning_effort` | string | `"no_think"`, `"low"`, `"high"` | Hy3 thinking mode switch. Use `"no_think"` for fast direct answers and `"high"` for harder reasoning/coding/math tasks. |

### Thinking / reasoning mode

Python SDK:

```python
response = client.chat.completions.create(
    model=MODEL,
    messages=[{"role": "user", "content": "Solve: 17 * 23"}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

Raw HTTP JSON body:

```json
{
  "model": "hy3",
  "messages": [{"role": "user", "content": "Solve: 17 * 23"}],
  "chat_template_kwargs": {"reasoning_effort": "high"}
}
```

If the server was launched with a reasoning parser, some frameworks may expose a `reasoning_content` field in the response message. For product UIs, prefer showing the final answer by default and log or summarize reasoning content only when your product policy allows it.

### Tool calling

To use automatic tool calling with vLLM, start the server with a Hy3-compatible tool parser and auto tool choice enabled. For SGLang, start the server with its Hy/Hunyuan tool parser. Then pass OpenAI-style `tools` and `tool_choice="auto"` in the request.

The application is responsible for:

1. defining tool schemas,
2. sending the user request with `tools`,
3. reading `message.tool_calls`,
4. executing the tool locally,
5. appending a `tool` message with the tool result,
6. calling the model again for the final answer.

See the [tool calling guide](examples/04_tool_calling.md) and [`examples/04_tool_calling.py`](examples/04_tool_calling.py).

## 6. Example index

For the complete list, see the [Examples Index](examples/README.md).

| Guide | Script | What it demonstrates |
| --- | --- | --- |
| [Basic chat](examples/01_basic_chat.md) | [`01_basic_chat.py`](examples/01_basic_chat.py) | Single-turn and multi-turn chat. |
| [Streaming](examples/02_streaming.md) | [`02_streaming.py`](examples/02_streaming.py) | Streaming request and per-chunk parsing. |
| [Latency compare](examples/03_latency_compare.md) | [`03_latency_compare.py`](examples/03_latency_compare.py) | Non-streaming vs streaming: first-token latency and total latency. |
| [Tool calling](examples/04_tool_calling.md) | [`04_tool_calling.py`](examples/04_tool_calling.py) | One tool call and a multi-turn tool execution loop. |
| [Reasoning mode](examples/05_reasoning_mode.md) | [`05_reasoning_mode.py`](examples/05_reasoning_mode.py) | `no_think` vs `high` reasoning mode comparison. |
| [Error handling & retry](examples/06_error_handling_retry.md) | [`06_error_handling_retry.py`](examples/06_error_handling_retry.py) | Timeout, rate-limit, network error retry with exponential backoff. |

Each `.md` file in `examples/` contains the full request, response parsing notes, and sample output.

## 7. Common errors and troubleshooting

| Symptom | Possible cause | Fix |
| --- | --- | --- |
| `Connection refused`, `Name or service not known` | Server is not running or `HY3_BASE_URL` is wrong. | Check host/port and run `curl ${HY3_BASE_URL}/models`. |
| HTTP `401` / `403` | API key mismatch in gateway or proxy. | Use the correct `HY3_API_KEY`. For local servers, `EMPTY` is often enough. |
| HTTP `404` or `model not found` | Request model name does not match server `--served-model-name`. | Set `HY3_MODEL=hy3` or inspect `/v1/models`. |
| HTTP `400` around chat template | Missing or incompatible chat template. | Use the Hy3 tokenizer/chat template or update serving framework. |
| `tool_calls` is empty when tools are expected | Tool parser is not enabled, tool schema is weak, or `tool_choice` is `none`. | Enable tool parser at server startup, set `tool_choice="auto"`, and provide a clear JSON schema. |
| Tool arguments are malformed | Automatic tool calling may not strictly constrain arguments in all modes. | Add `strict: true`, set `parallel_tool_calls=false`, validate JSON before executing tools, and retry or ask the model to regenerate. |
| Missing `reasoning_content` | Server did not enable reasoning parser or framework does not expose separate reasoning. | Enable Hy3/Hunyuan reasoning parser. Still use `reasoning_effort` to control the model behavior. |
| HTTP `429` | Gateway/proxy/server queue is rate limiting. | Retry with exponential backoff, reduce concurrency, lower `max_tokens`. |
| HTTP `500` / CUDA OOM | Context too long, `max_tokens` too high, too many concurrent requests, insufficient GPU memory. | Lower concurrency, reduce context/max tokens, adjust serving config, or use larger-memory GPUs. |
| Client timeout | First request/model load/long generation took too long. | Increase SDK timeout, lower `max_tokens`, use streaming for better perceived latency. |
