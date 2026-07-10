# Hy3 API Quickstart

[简体中文](quickstart_CN.md)

## Prerequisites

You need:

- A checkout of this repository and Python with `venv` and `pip`.
- Either a self-hosted Hy3 OpenAI-compatible endpoint or an OpenRouter account.
- For self-hosting, deploy Hy3 first with the repository's [vLLM](README.md#vllm) or [SGLang](README.md#sglang) command.

Create an isolated environment and install the example dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r examples/api/requirements.txt
cp examples/api/.env.example examples/api/.env
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` and copy the file with `Copy-Item examples/api/.env.example examples/api/.env`.

## API configuration

The examples load `examples/api/.env` without replacing variables already present in your shell.

| Variable | Self-hosted default | OpenRouter value | Purpose |
|---|---|---|---|
| `HY3_BACKEND` | `self_hosted` | `openrouter` | Selects request-body mapping. |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | `https://openrouter.ai/api/v1` | OpenAI-compatible API base URL. |
| `HY3_API_KEY` | `EMPTY` | Environment variable containing your OpenRouter key | Authentication passed to the SDK. |
| `HY3_MODEL` | `hy3` | `tencent/hy3:free` | Model sent in each request. |
| `HY3_TIMEOUT` | `120` | `120`, or another finite positive number | SDK timeout in seconds. |

Self-hosted `.env`:

```dotenv
HY3_BACKEND=self_hosted
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
HY3_TIMEOUT=120
```

OpenRouter configuration keeps the key in the environment:

```bash
# Set HY3_API_KEY in your shell or secret manager before running.
export HY3_BACKEND=openrouter
export HY3_BASE_URL=https://openrouter.ai/api/v1
export HY3_MODEL=tencent/hy3:free
export HY3_TIMEOUT=120
```

Windows PowerShell equivalent:

```powershell
# Set $env:HY3_API_KEY from your secret manager before running.
$env:HY3_BACKEND = "openrouter"
$env:HY3_BASE_URL = "https://openrouter.ai/api/v1"
$env:HY3_MODEL = "tencent/hy3:free"
$env:HY3_TIMEOUT = "120"
```

## Five-minute first call

After configuring one backend, run the first example from the repository root:

```bash
python examples/api/01_basic_chat.py
```

The script makes a single-turn request, appends the assistant content to the conversation, and then makes a second request. It also exposes normalized reasoning, finish reason, and usage when the backend supplies them. See the [basic chat guide](examples/api/01_basic_chat.md) for the complete request and deterministic test output.

## curl

Self-hosted raw HTTP JSON uses `chat_template_kwargs` at the top level. In Bash:

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer EMPTY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

In Windows PowerShell, use a single-quoted here-string to preserve the same raw JSON:

```powershell
$body = @'
{
  "model": "hy3",
  "messages": [{"role": "user", "content": "Hello!"}],
  "temperature": 0.9,
  "top_p": 1.0,
  "max_tokens": 256,
  "chat_template_kwargs": {"reasoning_effort": "no_think"}
}
'@

curl.exe http://127.0.0.1:8000/v1/chat/completions `
  -H "Content-Type: application/json" `
  --data-raw $body
```

OpenRouter raw HTTP JSON uses `reasoning` at the top level and reads the key from `${HY3_API_KEY}`. In Bash:

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer ${HY3_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tencent/hy3:free",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "reasoning": {"effort": "none"}
  }'
```

In Windows PowerShell, use the environment variable without copying the key into the command:

```powershell
$body = @'
{
  "model": "tencent/hy3:free",
  "messages": [{"role": "user", "content": "Hello!"}],
  "temperature": 0.9,
  "top_p": 1.0,
  "max_tokens": 256,
  "reasoning": {"effort": "none"}
}
'@

curl.exe https://openrouter.ai/api/v1/chat/completions `
  -H "Authorization: Bearer $env:HY3_API_KEY" `
  -H "Content-Type: application/json" `
  --data-raw $body
```

These are wire-format bodies. Neither curl body contains an SDK-only wrapper field.

## Python SDK

The OpenAI Python SDK accepts provider-specific body fields through `extra_body`.

Self-hosted:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
)
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={
        "chat_template_kwargs": {"reasoning_effort": "no_think"}
    },
)
print(response.choices[0].message.content)
```

OpenRouter:

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["HY3_API_KEY"],
)
response = client.chat.completions.create(
    model="tencent/hy3:free",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
    extra_body={"reasoning": {"effort": "none"}},
)
print(response.choices[0].message.content)
```

## Raw JSON versus SDK `extra_body`

`extra_body` is an OpenAI SDK argument, not an HTTP field. The SDK merges its contents into the outgoing JSON object.

| Backend | Raw curl JSON | Python SDK argument |
|---|---|---|
| Self-hosted | `chat_template_kwargs.reasoning_effort` at the body root | `extra_body={"chat_template_kwargs": {"reasoning_effort": effort}}` |
| OpenRouter | `reasoning.effort` at the body root | `extra_body={"reasoning": {"effort": mapped_effort}}` |

For OpenRouter, the examples map Hy3 `no_think` to `none`; `low` and `high` keep the same names.

## Parameters

| Parameter | Meaning in these examples |
|---|---|
| `temperature` | Sampling temperature. The examples use `0.9`. |
| `top_p` | Nucleus-sampling cutoff. The examples use `1.0`. |
| `max_tokens` | Maximum generated tokens; examples use `128`, `256`, or `512` depending on the task. |
| `stop` | Optional string or list of strings that stops generation when matched. It is not set by the six examples. |
| `stream` | Set `true` to receive chunks instead of one completion. |
| `stream_options` | Use `{"include_usage": true}` to request a usage-only terminal chunk when supported. |
| `tools` | Function schemas available to the model. |
| `tool_choice` | The tool example uses `auto`, allowing a response or one or more tool calls. |
| Reasoning effort | Self-hosted accepts `no_think`, `low`, or `high`; OpenRouter uses `none`, `low`, or `high` on the wire. |

## Reasoning mode

Use `no_think` for a direct response, `low` for lighter reasoning, and `high` for complex reasoning tasks. Reasoning fields are optional: a backend may return content without `reasoning`, `reasoning_content`, or `reasoning_details`, and that is a valid response state.

The [reasoning comparison example](examples/api/05_reasoning_mode.md) sends the same question, sampling parameters, and token limit for `no_think` and `high`; only the mapped effort changes. Do not expose private reasoning to end users without reviewing your product's policy and provider behavior.

## Streaming

Set `stream=True` and `stream_options={"include_usage": True}` with the SDK. A robust consumer must accept:

- chunks with an empty `choices` list;
- content and reasoning arriving in different deltas;
- interleaved tool-call fragments identified by `index`;
- a final usage-only chunk.

The shared `StreamAccumulator` handles these cases, prints content live, keeps reasoning separate, and sorts reconstructed tool calls by index. See [streaming](examples/api/02_streaming.md) and [streaming versus non-streaming](examples/api/03_streaming_vs_non_streaming.md).

## Tool calling

Tool calling requires both a request schema and a server launched with compatible parsers.

The repository's [vLLM deployment command](README.md#vllm) includes:

```text
--tool-call-parser hy_v3
--reasoning-parser hy_v3
--enable-auto-tool-choice
```

The documented [SGLang deployment command](README.md#sglang) uses:

```text
--tool-call-parser hunyuan
--reasoning-parser hunyuan
```

The [tool-calling guide](examples/api/04_tool_calling.md) demonstrates `tools`, `tool_choice="auto"`, multiple calls returned in one assistant turn, matching `tool_call_id` values, structured argument errors, and a bounded loop. The example executes those calls sequentially. Its Beijing/Shenzhen weather values are deterministic demo data, not live weather.

## Rate limits

Do not assume a fixed QPS, RPM, or TPM value:

- Self-hosted capacity depends on GPU memory, concurrency, model-server settings, and any gateway in front of the server.
- OpenRouter limits are dynamic and account/provider dependent.

Handle HTTP 429, honor a finite numeric `Retry-After` value when present, and otherwise use bounded backoff. The [retry guide](examples/api/06_error_handling_retry.md) shows this policy without publishing a fixed limit.

## Troubleshooting

| Symptom | Checks and corrective action |
|---|---|
| Connection refused | Confirm the self-hosted process is running, the port is `8000`, and `HY3_BASE_URL` ends in `/v1`. |
| HTTP 401 or 403 | Self-hosted examples use `EMPTY`; OpenRouter requires a valid key in the `HY3_API_KEY` environment variable. Do not put a real key in documentation or source control. |
| Model not found | Match `HY3_MODEL` to the served name: the repository deployment commands expose `hy3`; OpenRouter uses `tencent/hy3:free`. |
| Invalid or unknown fields | Send `chat_template_kwargs` or `reasoning` at the raw JSON body root. Use `extra_body` only as an SDK call argument. |
| Context overflow | Reduce conversation history, tool payloads, or `max_tokens`; Hy3's published context length does not remove server-side token and memory constraints. |
| Empty stream | Accept empty-choice chunks, verify `stream=True`, and inspect the final accumulated result rather than assuming every chunk has content. |
| Missing tool calls | Confirm the server parser flags, `tools` schema, and `tool_choice`. The model may legitimately answer without calling a tool. |
| Missing reasoning | Reasoning fields are optional. Check the selected effort and backend mapping; do not treat absent reasoning as a malformed completion. |
| HTTP 429 | Honor a finite numeric `Retry-After`; otherwise use bounded jittered retry. OpenRouter limits are dynamic. |
| Transient 5xx or transport errors | Retry only a bounded number of times and re-raise the final error. Do not retry permanent 4xx errors such as 400, 401, 403, or 404. |
| Self-hosted CUDA out of memory | Reduce concurrency or token limits, review tensor parallelism and GPU capacity, and compare your launch command with the repository's vLLM/SGLang deployment section. |

## Examples learning path

Continue with the [API examples index](examples/api/README.md):

1. [Basic chat](examples/api/01_basic_chat.md)
2. [Streaming](examples/api/02_streaming.md)
3. [Streaming versus non-streaming](examples/api/03_streaming_vs_non_streaming.md)
4. [Tool calling](examples/api/04_tool_calling.md)
5. [Reasoning mode](examples/api/05_reasoning_mode.md)
6. [Error handling and retry](examples/api/06_error_handling_retry.md)

Every guide links to its runnable `.py` file and Chinese counterpart.
