# Hy3 API Quickstart

This guide helps developers:

* make a first Hy3 API call in about five minutes
* understand the main request parameters
* use both self-hosted and managed OpenAI-compatible endpoints
* find runnable examples for chat, streaming, tool calling, reasoning, latency, and retries

## 1. Choose an endpoint

Hy3 can be accessed through different serving environments.

This guide distinguishes between:

1. a self-hosted Hy3 OpenAI-compatible server
2. Tencent Cloud TokenHub

### Self-hosted Hy3

After deploying Hy3 with a compatible serving stack such as vLLM or SGLang, the local defaults used by the Hy3 repository are:

| Item          | Default                    |
| ------------- | -------------------------- |
| Base URL      | `http://127.0.0.1:8000/v1` |
| Chat endpoint | `/chat/completions`        |
| API key       | `EMPTY`                    |
| Model         | `hy3`                      |

A complete chat URL is therefore:

```text
http://127.0.0.1:8000/v1/chat/completions
```

The local server must already be running before client requests can succeed.

### Tencent Cloud TokenHub

For a managed OpenAI-compatible endpoint, Tencent Cloud TokenHub can be used.

Example configuration for the Guangzhou region:

| Item          | Value                                 |
| ------------- | ------------------------------------- |
| Base URL      | `https://tokenhub.tencentmaas.com/v1` |
| Chat endpoint | `/chat/completions`                   |
| API key       | TokenHub API Key                      |
| Model         | `hy3`                                 |

A complete chat URL is:

```text
https://tokenhub.tencentmaas.com/v1/chat/completions
```

Use the endpoint that matches the region where the service is enabled.

## 2. API key security

Never commit a real API key to Git.

Do not put a real key in:

```text
.env.example
Python source files
Markdown examples
Git commits
Pull Request descriptions
```

For a self-hosted local server that does not require authentication, the repository examples use:

```text
HY3_API_KEY=EMPTY
```

For a managed endpoint, store the real API key in an environment variable.

### PowerShell

```powershell
$env:HY3_API_KEY="YOUR_API_KEY"
```

### Bash or zsh

```bash
export HY3_API_KEY="YOUR_API_KEY"
```

## 3. Environment variables

The examples in this directory use:

```text
HY3_BASE_URL
HY3_API_KEY
HY3_MODEL
```

### Self-hosted configuration

PowerShell:

```powershell
$env:HY3_BASE_URL="http://127.0.0.1:8000/v1"
$env:HY3_API_KEY="EMPTY"
$env:HY3_MODEL="hy3"
```

Bash or zsh:

```bash
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"
export HY3_MODEL="hy3"
```

### Tencent Cloud TokenHub configuration

PowerShell:

```powershell
$env:HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
$env:HY3_API_KEY="YOUR_API_KEY"
$env:HY3_MODEL="hy3"
```

Bash or zsh:

```bash
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
export HY3_API_KEY="YOUR_API_KEY"
export HY3_MODEL="hy3"
```

## 4. Install the Python SDK

Create and activate a virtual environment.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Linux or macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the OpenAI Python SDK:

```bash
python -m pip install -r examples/api/requirements.txt
```

Verify the installation:

```bash
python -c "import openai; print(openai.__version__)"
```

## 5. Five-minute first call with curl

### Option A: self-hosted Hy3

```bash
curl -X POST "http://127.0.0.1:8000/v1/chat/completions" \
  -H "Authorization: Bearer EMPTY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {
        "role": "user",
        "content": "Hello! Can you briefly introduce yourself?"
      }
    ],
    "temperature": 0.9,
    "top_p": 1.0
  }'
```

### Option B: Tencent Cloud TokenHub

```bash
curl -X POST "https://tokenhub.tencentmaas.com/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {
        "role": "user",
        "content": "Hello! Can you briefly introduce yourself?"
      }
    ],
    "temperature": 0.9,
    "top_p": 1.0
  }'
```

Replace:

```text
YOUR_API_KEY
```

with a valid API key for the managed endpoint.

### Example response structure

Generated text and token counts vary between requests.

```json
{
  "id": "example-response-id",
  "object": "chat.completion",
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm Hunyuan..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 18,
    "completion_tokens": 31,
    "total_tokens": 49
  }
}
```

The main generated text is located at:

```text
choices[0].message.content
```

## 6. Five-minute first call with the OpenAI Python SDK

Create a file such as:

```text
first_call.py
```

Add:

```python
import os

from openai import OpenAI


client = OpenAI(
    base_url=os.getenv(
        "HY3_BASE_URL",
        "http://127.0.0.1:8000/v1",
    ),
    api_key=os.getenv(
        "HY3_API_KEY",
        "EMPTY",
    ),
)

response = client.chat.completions.create(
    model=os.getenv(
        "HY3_MODEL",
        "hy3",
    ),
    messages=[
        {
            "role": "user",
            "content": (
                "Hello! Can you briefly "
                "introduce yourself?"
            ),
        }
    ],
    temperature=0.9,
    top_p=1.0,
)

print(
    response
    .choices[0]
    .message
    .content
)
```

Run:

```bash
python first_call.py
```

Example output:

```text
Hello! I'm Hunyuan, a large model developed by Tencent...
```

The exact generated text may vary.

## 7. Core request parameters

### `temperature`

Controls sampling randomness.

Example:

```python
temperature=0.9
```

Lower values generally make output more deterministic and focused.

Higher values generally allow more variation.

Example use cases:

```text
lower temperature
→ extraction
→ deterministic formatting
→ focused answers

higher temperature
→ brainstorming
→ creative writing
→ varied outputs
```

The Hy3 repository quickstart recommends:

```python
temperature=0.9
```

with:

```python
top_p=1.0
```

### `top_p`

Controls nucleus sampling.

Example:

```python
top_p=1.0
```

Lower values restrict sampling to a smaller probability mass.

In most applications, avoid aggressively tuning both `temperature` and `top_p` at the same time unless you have a specific evaluation plan.

### `max_tokens`

Limits the maximum number of output tokens for one response.

Example:

```python
max_tokens=1000
```

Tokens are not the same as characters or words.

For reasoning-capable configurations, reasoning tokens and final-answer tokens may share the available output budget depending on the serving environment.

### `stop`

Stops generation when one of the specified sequences is reached.

Example:

```python
stop=["END"]
```

Multiple stop sequences can be supplied:

```python
stop=[
    "END",
    "###",
]
```

The stop sequence itself may be omitted from returned output depending on endpoint behavior.

### `tools`

Defines functions that the model may request the client application to execute.

Example:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get weather data for a city."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string"
                    }
                },
                "required": ["city"],
            },
        },
    }
]
```

Request:

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {
            "role": "user",
            "content": (
                "What is the weather in Tokyo?"
            ),
        }
    ],
    tools=tools,
)
```

A model may return a structured tool call instead of a final answer.

The client application is responsible for:

1. validating the tool name
2. parsing tool arguments
3. executing trusted application code
4. sending the tool result back with `role="tool"`
5. requesting the final assistant answer

See:

```text
examples/api/04_tool_calling.py
examples/api/04_tool_calling.md
```

for a complete multi-turn tool loop.

## 8. Reasoning mode

Reasoning configuration depends on the serving environment.

Do not assume that every OpenAI-compatible endpoint accepts the same reasoning field layout.

### Self-hosted Hy3

The Hy3 repository quickstart configures reasoning through serving-specific chat-template arguments:

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {
            "role": "user",
            "content": (
                "Solve this reasoning problem."
            ),
        }
    ],
    extra_body={
        "chat_template_kwargs": {
            "reasoning_effort": "high"
        }
    },
)
```

Example modes include:

```text
no_think
low
high
```

Use `no_think` for direct responses and `high` for more complex reasoning tasks when supported by the serving environment.

### Tencent Cloud TokenHub

For the managed TokenHub endpoint used by these examples, reasoning effort is sent as a top-level request-body field through `extra_body`:

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {
            "role": "user",
            "content": (
                "Solve this reasoning problem."
            ),
        }
    ],
    extra_body={
        "reasoning_effort": "high"
    },
)
```

The examples treat reasoning metadata as optional because endpoint behavior can vary.

Possible observable fields include:

```text
reasoning_content
completion_tokens_details.reasoning_tokens
```

See:

```text
examples/api/05_reasoning_mode.py
examples/api/05_reasoning_mode.md
```

for a complete comparison.

## 9. Streaming

Enable streaming with:

```python
stream=True
```

Example:

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[
        {
            "role": "user",
            "content": "Explain what an API is.",
        }
    ],
    stream=True,
)

for chunk in stream:
    if not chunk.choices:
        continue

    content = chunk.choices[0].delta.content

    if content is not None:
        print(
            content,
            end="",
            flush=True,
        )
```

Streaming can improve perceived responsiveness because users can see content before the complete response finishes.

It does not guarantee lower total latency.

See:

```text
examples/api/02_streaming.py
examples/api/03_latency_compare.py
```

## 10. Rate limits

Hy3 does not have one universal numeric API rate limit that applies to every deployment.

Rate limiting depends on the serving environment.

### Self-hosted deployment

Limits depend on factors such as:

```text
GPU capacity
server configuration
concurrency controls
gateway settings
application-level throttling
```

Configure limits according to your own infrastructure.

### Managed endpoint

Managed providers may enforce account-, key-, model-, service-, RPM-, concurrency-, quota-, or plan-specific limits.

When a rate limit is exceeded, an endpoint may return:

```text
HTTP 429
```

Do not hard-code an undocumented universal requests-per-minute value.

When available:

1. inspect the provider error response
2. respect `Retry-After`
3. retry transient failures with bounded backoff
4. avoid unlimited retry loops

See:

```text
examples/api/06_error_handling_retry.py
examples/api/06_error_handling_retry.md
```

## 11. Common errors and troubleshooting

### Connection error

Typical symptoms:

```text
APIConnectionError
Connection refused
Connection error
```

Check:

```text
Is the API server running?
Is the Base URL correct?
Is the port correct?
Can the client reach the server?
Is a firewall or proxy blocking the connection?
```

For self-hosted defaults, verify that a service is actually listening on:

```text
127.0.0.1:8000
```

### HTTP 400 — invalid request

Possible causes:

```text
missing model
invalid parameter value
unsupported request field
malformed messages
endpoint-specific parameter mismatch
```

Check the complete request payload.

Reasoning configuration is a common compatibility point because self-hosted and managed serving environments may use different field layouts.

### HTTP 401 — authentication failure

Possible causes:

```text
missing API key
invalid API key
disabled API key
incorrect Authorization header
```

Managed APIs commonly expect:

```text
Authorization: Bearer YOUR_API_KEY
```

Never print or commit the real key while debugging.

### HTTP 403 — permission failure

Possible causes:

```text
API key lacks access to the model
IP whitelist restriction
service permission restriction
```

Check the API key's configured access scope.

### HTTP 404 — not found

Possible causes:

```text
wrong Base URL
wrong endpoint path
incorrect service route
```

For Chat Completions, verify:

```text
/v1/chat/completions
```

relative to the provider configuration.

### HTTP 429 — rate limited

The request rate or another quota dimension has been exceeded.

Recommended actions:

```text
reduce request rate
inspect provider quota
respect Retry-After when present
use bounded exponential backoff with jitter
```

Do not retry immediately in a tight loop.

### HTTP 5xx — transient server failure

Examples include:

```text
500
502
503
504
```

Possible causes:

```text
temporary upstream overload
gateway failure
dependency failure
service unavailable
timeout
```

For transient failures, use bounded retries.

Do not retry indefinitely.

### Timeout

Possible causes:

```text
long generation
large max_tokens
high reasoning effort
server load
network instability
```

Possible actions:

```text
increase the client timeout when appropriate
reduce output length
inspect server health
retry transient timeouts with limits
```

### Model not found or unavailable

Verify:

```text
HY3_MODEL=hy3
```

For custom managed services, the service ID may differ from the public model name.

### Empty or missing `tool_calls`

Possible causes:

```text
the model chose not to use a tool
tool schema is unclear
the prompt does not require a tool
the serving stack lacks the required tool-call parser
```

For debugging, inspect the complete response and verify the serving configuration.

### Reasoning mode appears unchanged

Check:

```text
which serving environment is being used
where reasoning_effort is placed in the request body
whether the endpoint supports the requested mode
whether reasoning metadata is exposed
```

Do not assume self-hosted and managed endpoints use identical request layouts.

## 12. Runnable examples

The examples are independent and can be run from the repository root.

### 1. Basic chat

Single-turn and multi-turn conversation:

```bash
python examples/api/01_basic_chat.py
```

Documentation:

```text
examples/api/01_basic_chat.md
```

### 2. Streaming

Chunk-by-chunk parsing and full response reconstruction:

```bash
python examples/api/02_streaming.py
```

Documentation:

```text
examples/api/02_streaming.md
```

### 3. Non-streaming vs streaming latency

Measures:

```text
non-streaming total latency
client-observed TTFT
streaming total latency
chunk count
```

Run:

```bash
python examples/api/03_latency_compare.py
```

Documentation:

```text
examples/api/03_latency_compare.md
```

### 4. Tool calling

Demonstrates:

```text
single tool call
JSON argument parsing
local function execution
role="tool"
tool_call_id
multi-turn tool loop
```

Run:

```bash
python examples/api/04_tool_calling.py
```

Documentation:

```text
examples/api/04_tool_calling.md
```

### 5. Reasoning mode

Compares:

```text
no_think
high
latency
reasoning tokens
optional reasoning content
final answer behavior
```

Run:

```bash
python examples/api/05_reasoning_mode.py
```

Documentation:

```text
examples/api/05_reasoning_mode.md
```

### 6. Error handling and retry

Live request:

```bash
python examples/api/06_error_handling_retry.py
```

Simulated timeout:

```bash
python examples/api/06_error_handling_retry.py --simulate timeout
```

Simulated rate limit:

```bash
python examples/api/06_error_handling_retry.py --simulate rate_limit
```

Simulated connection failure:

```bash
python examples/api/06_error_handling_retry.py --simulate connection
```

Simulated server failure:

```bash
python examples/api/06_error_handling_retry.py --simulate server
```

Documentation:

```text
examples/api/06_error_handling_retry.md
```

## 13. Recommended learning path

For a first-time Hy3 API developer:

```text
5 minutes
→ first curl request
→ first Python request

10 minutes
→ basic single-turn and multi-turn chat

15 minutes
→ streaming chunk parsing

20 minutes
→ streaming latency and TTFT

25 minutes
→ tool calling and tool loop

30 minutes
→ reasoning modes and retry handling
```

## 14. Security checklist

Before committing changes:

```text
[ ] No real API key in source files
[ ] No real API key in Markdown
[ ] No real API key in Git history
[ ] Secrets are stored outside tracked files
[ ] Tool names and arguments are validated
[ ] Retry loops have hard limits
[ ] Mock data is clearly labeled as mock data
```
