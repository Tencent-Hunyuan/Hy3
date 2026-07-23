# Hy3 API quickstart

This guide gets a developer from a running Hy3 server to a first response in
about five minutes, then introduces the main API capabilities through six
runnable examples.

Hy3 exposes an OpenAI-compatible Chat Completions API when served with vLLM or
SGLang. The repository's [deployment guide](./README.md#deployment) explains how
to start either server.

## 1. Connection basics

| Setting | Local default | Notes |
| --- | --- | --- |
| Base URL | `http://127.0.0.1:8000/v1` | Keep the `/v1` suffix. |
| API key | `EMPTY` | Local servers normally accept any non-empty value. A hosted endpoint requires its real key. |
| Model | `hy3` | Must match the server's `--served-model-name`. |
| Timeout | `120` seconds | Increase for long context or `high` reasoning. |

Self-hosted Hy3 has no fixed API-level QPS or token-per-minute quota. Effective
throughput depends on GPU memory, server concurrency, context length, and
generation length. A gateway or hosted provider may return HTTP `429`; follow
its published quota and `Retry-After` header rather than assuming a universal
limit.

Never commit a real API key. The examples read all connection information from
environment variables.

## 2. First call in five minutes

### Prerequisites

- Python 3.10 or newer
- A Hy3 vLLM or SGLang endpoint
- `curl` for the HTTP example

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r examples/api/requirements.txt

cp examples/api/.env.example examples/api/.env
```

The default `.env` targets a local server. To use another endpoint, edit the
copy without committing it:

```dotenv
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
HY3_TIMEOUT=120
```

Confirm that the server advertises the model:

```bash
curl "$HY3_BASE_URL/models" \
  -H "Authorization: Bearer $HY3_API_KEY"
```

If the variables only exist in `examples/api/.env`, export them before using
`curl`; the Python examples load that file automatically.

### Minimal curl request

```bash
curl --fail-with-body --silent --show-error \
  "$HY3_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H "Content-Type: application/json" \
  -d @- <<'JSON'
{
  "model": "hy3",
  "messages": [
    {"role": "user", "content": "Explain what an API is in one sentence."}
  ],
  "temperature": 0.9,
  "top_p": 1.0,
  "max_tokens": 128,
  "chat_template_kwargs": {"reasoning_effort": "no_think"}
}
JSON
```

### Minimal Python request

```python
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv("examples/api/.env")

client = OpenAI(
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    timeout=float(os.getenv("HY3_TIMEOUT", "120")),
)

response = client.chat.completions.create(
    model=os.getenv("HY3_MODEL", "hy3"),
    messages=[
        {"role": "user", "content": "Explain what an API is in one sentence."}
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)

choice = response.choices[0]
print(choice.message.content)
print("finish_reason:", choice.finish_reason)
if response.usage:
    print("total_tokens:", response.usage.total_tokens)
```

An OpenAI-compatible response has this shape (content and counts vary):

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "An API is ..."},
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 24,
    "total_tokens": 42
  }
}
```

Treat the values above as a schema illustration, not a captured benchmark.

## 3. Request parameters

### `temperature`

Controls sampling randomness. Lower values favor repeatability; higher values
allow more variation. Hy3's repository recommends `0.9`. For latency comparisons
and deterministic tool arguments, these examples use `0.0` where appropriate.

### `top_p`

Limits sampling to the smallest token set whose cumulative probability reaches
the supplied value. Hy3's repository recommends `1.0`. Tune `temperature` first
instead of changing both controls at once.

### `max_tokens`

Caps generated tokens. A small cap lowers latency and cost but may produce
`finish_reason="length"`. Input plus generated tokens must fit the served
context window. Reasoning modes also consume generation budget, so allow a
larger cap for `high`.

### `stop`

A string or list of strings that ends generation when matched. Stop sequences
are omitted from most examples because accidental matches can truncate prose.

```python
response = client.chat.completions.create(
    ...,
    stop=["END_OF_ANSWER"],
)
```

### `tools`

Declare functions with JSON Schema in the OpenAI `tools` format. The model may
return `message.tool_calls`; the application must validate arguments, execute
the named function, then append one `role="tool"` message per call.

For vLLM, start Hy3 with:

```text
--tool-call-parser hy_v3 --enable-auto-tool-choice
```

For SGLang, use its Hy3 `hunyuan` tool-call parser as shown in the deployment
recipe. See [example 04](./examples/api/04_tool_calling.md) for a bounded loop.

### Reasoning mode

Pass the Hy3 extension through `extra_body` when using the Python SDK:

```python
extra_body={
    "chat_template_kwargs": {
        "reasoning_effort": "no_think"  # or "low" / "high"
    }
}
```

| Value | Suggested use |
| --- | --- |
| `no_think` | Direct answers and lowest latency |
| `low` | Moderate planning or multi-constraint tasks |
| `high` | Math, coding, and difficult reasoning |

The server must be started with the matching reasoning parser (`hy_v3` for
vLLM or `hunyuan` for SGLang). When provided by the server, reasoning is exposed
separately as `message.reasoning_content`. Applications should use
`message.content` as the final user-facing answer.

## 4. Runnable examples

Run every script from the repository root:

| Example | Command | Demonstrates |
| --- | --- | --- |
| Basic chat | `python examples/api/01_basic_chat.py` | Single and multi-turn history |
| Streaming | `python examples/api/02_streaming.py` | Chunk parsing and TTFT |
| Latency comparison | `python examples/api/03_latency_comparison.py` | Repeated non-stream/stream timing |
| Tool calling | `python examples/api/04_tool_calling.py` | JSON arguments and bounded tool loop |
| Reasoning modes | `python examples/api/05_reasoning_modes.py` | `no_think`, `low`, and `high` |
| Error handling | `python examples/api/06_error_handling_retry.py` | Retry classification and backoff |

Each script has a companion walkthrough under [`examples/api`](./examples/api/).

## 5. Troubleshooting

| Symptom | Likely cause | Check or fix |
| --- | --- | --- |
| Connection refused | Server is not listening or URL is wrong | Run `curl $HY3_BASE_URL/models`; inspect server logs and port. |
| HTTP 401/403 | Missing or invalid key | Set a non-empty local key or the hosted provider's real key. Do not log it. |
| HTTP 404 / model not found | Wrong `/v1` path or served model name | List `/models`; align `HY3_MODEL` with `--served-model-name`. |
| HTTP 429 | Gateway/concurrency quota | Honor `Retry-After`, reduce concurrency, and use bounded backoff. |
| Timeout | Queueing, long context, or deep reasoning | Increase `HY3_TIMEOUT`, reduce input/output length, and inspect server load. |
| Empty `reasoning_content` | Direct mode or missing parser | Use `low`/`high` and start the server with the Hy3 reasoning parser. |
| No `tool_calls` | Parser not enabled or model answered directly | Enable the tool parser; use `tool_choice="auto"` and a precise tool description. |
| `finish_reason="length"` | Output cap reached | Increase `max_tokens` or shorten the prompt. |
| CUDA out of memory | Model/context/concurrency exceeds GPU memory | Reduce max model length or concurrency; follow the 8-GPU deployment recipe. |

Do not retry malformed requests, authentication failures, or model-not-found
responses. Fix those errors first. Example 06 retries only connection failures,
timeouts, rate limits, and selected transient server responses.

## 6. Validate the examples

Offline checks do not require a model or API key:

```bash
python -m pip install -r examples/api/requirements-dev.txt
ruff format --check --config examples/api/ruff.toml examples/api
ruff check --config examples/api/ruff.toml examples/api
pytest -q examples/api/tests
```

Then run all six scripts against the target endpoint. Record the endpoint type,
date, and redacted outputs in a pull request; never claim a live verification
from offline tests alone.
