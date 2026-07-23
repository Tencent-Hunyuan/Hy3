# Hy3 API Quickstart

Get your first Hy3 API call running in 5 minutes, and master the full feature set in 30 minutes.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [5-Minute Quickstart](#5-minute-quickstart)
  - [1. Deploy Hy3](#1-deploy-hy3)
  - [2. Your First Call (curl)](#2-your-first-call-curl)
  - [3. Your First Call (Python SDK)](#3-your-first-call-python-sdk)
- [API Reference](#api-reference)
  - [Base Information](#base-information)
  - [Request Parameters](#request-parameters)
  - [Response Structure](#response-structure)
- [Reasoning Mode](#reasoning-mode)
- [Tool Calling](#tool-calling)
- [Rate Limits & Concurrency](#rate-limits--concurrency)
- [Troubleshooting](#troubleshooting)
- [Examples](#examples)

---

## Prerequisites

- **Deployed Hy3 server** via vLLM or SGLang (see [Deployment](#1-deploy-hy3) below).
- **Python 3.10+** with `openai` SDK installed:
  ```bash
  pip install openai
  ```
- The API is **OpenAI-compatible** — you can use any OpenAI SDK or HTTP client.

---

## 5-Minute Quickstart

### 1. Deploy Hy3

Choose one of the deployment options below to start a local API server.

<details>
<summary><b>Option A: vLLM (recommended)</b></summary>

```bash
# Build vLLM from source
uv venv --python 3.12 --seed --managed-python
source .venv/bin/activate
git clone https://github.com/vllm-project/vllm.git
cd vllm
uv pip install --editable . --torch-backend=auto

# Start the server with MTP speculative decoding
export VLLM_FLASHINFER_ALLREDUCE_BACKEND=trtllm

vllm serve tencent/Hy3 \
  --tensor-parallel-size 8 \
  --speculative-config.method mtp \
  --speculative-config.num_speculative_tokens 2 \
  --tool-call-parser hy_v3 \
  --reasoning-parser hy_v3 \
  --enable-auto-tool-choice \
  --port 8000 \
  --served-model-name hy3
```

> **Hardware**: 8×H20-3e (or GPUs with ≥80GB VRAM) for full BF16 deployment.

</details>

<details>
<summary><b>Option B: SGLang</b></summary>

```bash
git clone https://github.com/sgl-project/sglang
cd sglang
pip3 install pip --upgrade
pip3 install "transformers>=5.6.0"
pip3 install -e "python"

python3 -m sglang.launch_server \
  --model tencent/Hy3 \
  --tp-size 8 \
  --tool-call-parser hunyuan \
  --reasoning-parser hunyuan \
  --speculative-num-steps 2 \
  --speculative-eagle-topk 1 \
  --speculative-num-draft-tokens 3 \
  --speculative-algorithm EAGLE \
  --port 8000 \
  --served-model-name hy3
```

</details>

<details>
<summary><b>Option C: Third-party API endpoint</b></summary>

If you are using a hosted Hy3 endpoint (e.g., from Tencent Cloud or a partner platform), replace the base URL and API key with the ones provided by your platform. The API interface remains the same.

</details>

Once the server is running, verify it's reachable:

```bash
curl http://127.0.0.1:8000/v1/models
```

### 2. Your First Call (curl)

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "Hello! Can you briefly introduce yourself?"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256
  }'
```

**Expected response:**

```json
{
  "id": "chatcmpl-xxxxxxxx",
  "object": "chat.completion",
  "created": 1719000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm Hy3, a 295B-parameter Mixture-of-Experts large language model developed by Tencent's Hunyuan team..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 44,
    "total_tokens": 59
  }
}
```

### 3. Your First Call (Python SDK)

```python
from openai import OpenAI

# Initialize client — base_url points to your local server
client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",  # No authentication needed for local deployment
)

# Make your first call
response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "Hello! Can you briefly introduce yourself?"},
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=256,
)

# Print the response
print(response.choices[0].message.content)
```

> ✅ **You're done!** You've made your first Hy3 API call. Read on for the full API reference, or jump to the [Examples](#examples) section.

---

## API Reference

### Base Information

| Item | Value |
|:---|:---|
| **Base URL** | `http://127.0.0.1:8000/v1` (local default) |
| **API Key** | `EMPTY` (local deployment) or your platform key |
| **Model Name** | `hy3` |
| **API Protocol** | OpenAI-compatible `/v1/chat/completions` |
| **Context Length** | 256K tokens |
| **Supported Methods** | Chat completions (sync + streaming), tool calling, reasoning mode |

### Request Parameters

#### Required

| Parameter | Type | Description |
|:---|:---|:---|
| `model` | `string` | Model name. Use `"hy3"`. |
| `messages` | `array` | List of message objects. See [Message Format](#message-format). |

#### Optional

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `temperature` | `float` | `0.9` | Sampling temperature (0–2.0). Higher = more creative. **Recommended: 0.9**. |
| `top_p` | `float` | `1.0` | Nucleus sampling threshold (0–1.0). **Recommended: 1.0**. |
| `max_tokens` | `int` | model max | Maximum tokens to generate. If omitted, the model generates until a stop condition. |
| `stop` | `string` / `array` | — | Stop sequence(s). Generation stops when any sequence is encountered. |
| `stream` | `bool` | `false` | If `true`, the response is streamed as server-sent events (SSE). |
| `tools` | `array` | — | List of tool definitions for function calling. See [Tool Calling](#tool-calling). |
| `tool_choice` | `string` / `object` | `"auto"` | Tool selection strategy: `"auto"`, `"none"`, `"required"`, or a specific tool. |
| `seed` | `int` | — | Random seed for reproducible outputs. |
| `extra_body` | `object` | — | Extra parameters passed to the backend. Used for reasoning mode. |

#### Reasoning Mode (via `extra_body`)

| Parameter | Type | Default | Description |
|:---|:---|:---|:---|
| `extra_body.chat_template_kwargs.reasoning_effort` | `string` | `"no_think"` | `"no_think"` — direct response; `"low"` — brief reasoning; `"high"` — deep chain-of-thought. |

### Message Format

```json
{
  "role": "system | user | assistant | tool",
  "content": "message text or multimodal content",
  "tool_calls": [{"id": "...", "type": "function", "function": {"name": "...", "arguments": "..."}}],
  "tool_call_id": "..."  // only for role: "tool"
}
```

### Response Structure

**Non-streaming:**

```json
{
  "id": "chatcmpl-xxxxxxxx",
  "object": "chat.completion",
  "created": 1719000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "response text...",
        "tool_calls": []
      },
      "finish_reason": "stop | length | tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 44,
    "total_tokens": 59
  }
}
```

**Streaming (SSE):**

```
data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"content":"!"},"finish_reason":null}]}

data: {"id":"...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{},"finish_reason":"stop"}],"usage":{...}}

data: [DONE]
```

---

## Reasoning Mode

Hy3 supports both **fast thinking** (direct response) and **slow thinking** (chain-of-thought reasoning):

| Mode | `reasoning_effort` | Best for | Latency |
|:---|:---|:---|:---|
| **Fast** | `"no_think"` (default) | Simple Q&A, chat, translation, summarization | Lowest |
| **Reasoning** | `"low"` | Moderate reasoning, planning, analysis | Medium |
| **Deep reasoning** | `"high"` | Math proofs, complex coding, multi-step logic | Highest |

```python
# Fast thinking (default)
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "What is 2+2?"}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
)

# Deep reasoning
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Prove the Pythagorean theorem."}],
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

When reasoning mode is on, the model's thinking process is returned in `reasoning_content` and the final answer in `content`. In streaming mode, watch for `delta.reasoning_content` vs `delta.content`.

> ⚠️ **Note**: `reasoning_effort` is passed via `extra_body` (not as a top-level parameter). This is because the reasoning mode is implemented at the chat-template level in vLLM/SGLang.

---

## Tool Calling

Hy3 supports OpenAI-compatible function calling. Define tools in the request, and the model returns structured `tool_calls`:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"],
            },
        },
    }
]

response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "What's the weather in Beijing?"}],
    tools=tools,
    tool_choice="auto",
)

# Check for tool calls
if response.choices[0].message.tool_calls:
    for tc in response.choices[0].message.tool_calls:
        print(f"Function: {tc.function.name}")
        print(f"Arguments: {tc.function.arguments}")
```

See [Example 4: Tool Calling](examples/04-tool-calling.md) for a complete multi-turn tool loop.

---

## Rate Limits & Concurrency

| Aspect | Local Deployment | Hosted Platform |
|:---|:---|:---|
| **Rate limit** | Limited only by GPU throughput | Check your platform's tier |
| **Concurrency** | Tune via `--max-num-seqs` in vLLM | Per API key quota |
| **Context length** | 256K tokens | 256K tokens |

For local vLLM deployments, control concurrency with:

```bash
vllm serve tencent/Hy3 --max-num-seqs 256 ...
```

---

## Troubleshooting

### Common Errors

<details>
<summary><b>Connection refused: <code>http://127.0.0.1:8000</code></b></summary>

**Cause**: The server is not running or not listening on port 8000.

**Fix**:
1. Check if the server process is running.
2. Verify the port with `curl http://127.0.0.1:8000/v1/models`.
3. Check server logs for startup errors (common: insufficient GPU memory).
</details>

<details>
<summary><b><code>404 Not Found</code> on <code>/v1/chat/completions</code></b></summary>

**Cause**: Wrong URL path or the server doesn't serve the chat completions endpoint.

**Fix**: Ensure the full URL is `http://127.0.0.1:8000/v1/chat/completions` (note the `/v1` prefix).
</details>

<details>
<summary><b><code>model "hy3" not found</code> or <code>400 Bad Request</code></b></summary>

**Cause**: The model name doesn't match what the server expects.

**Fix**: Check `--served-model-name` in your server launch command. It should be `hy3`. Verify with `GET /v1/models`.
</details>

<details>
<summary><b><code>CUDA out of memory</code></b></summary>

**Cause**: Insufficient GPU memory.

**Fix**:
1. Reduce `--max-model-len` (e.g., `--max-model-len 32768` for 32K instead of 256K).
2. Use FP8 quantized weights (`tencent/Hy3-FP8`).
3. Increase tensor parallelism (`--tensor-parallel-size`).
4. Enable CPU offloading if supported.
</details>

<details>
<summary><b>Streaming: chunks arrive slowly or in large bursts</b></summary>

**Cause**: Server-side batching or MTP speculative decoding settings.

**Fix**:
1. Reduce `--speculative-config.num_speculative_tokens` for vLLM.
2. Check client-side buffering — use `stream=True` and iterate chunks without accumulation.
</details>

<details>
<summary><b><code>Reasoning mode has no effect</code></b></summary>

**Cause**: The `reasoning_effort` must be passed via `extra_body.chat_template_kwargs`, not as a top-level parameter.

**Fix**:
```python
# Correct ✅
extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}}

# Wrong ❌
reasoning_effort="high"
```
</details>

<details>
<summary><b>Tool calls not returned</b></summary>

**Cause**: Server not configured with tool-call parser, or tool schema is invalid.

**Fix**:
1. Ensure `--tool-call-parser hy_v3` (vLLM) or `--tool-call-parser hunyuan` (SGLang) is set.
2. Ensure `--enable-auto-tool-choice` (vLLM) is set for automatic tool selection.
3. Verify your tool schema follows the OpenAI function-calling format.
</details>

---

## Examples

Each example below includes a standalone Python script and a detailed walkthrough. Start with Example 1 if you're new to the API.

| # | Example | What You'll Learn | Files |
|:---|:---|:---|:---|
| 1 | **Basic Chat** | Single-turn and multi-turn conversations | [.md](examples/01-basic-chat.md) / [.py](examples/01-basic-chat.py) |
| 2 | **Streaming** | Streaming requests with chunk-by-chunk parsing | [.md](examples/02-streaming.md) / [.py](examples/02-streaming.py) |
| 3 | **Latency Comparison** | Non-streaming vs streaming: TTFT, total time | [.md](examples/03-latency-comparison.md) / [.py](examples/03-latency-comparison.py) |
| 4 | **Tool Calling** | Function definitions, tool loops, multi-turn execution | [.md](examples/04-tool-calling.md) / [.py](examples/04-tool-calling.py) |
| 5 | **Reasoning Mode** | Fast vs. deep thinking — when and how to use | [.md](examples/05-reasoning-mode.md) / [.py](examples/05-reasoning-mode.py) |
| 6 | **Error Handling** | Retries, backoff, timeout, rate-limit handling | [.md](examples/06-error-handling.md) / [.py](examples/06-error-handling.py) |
