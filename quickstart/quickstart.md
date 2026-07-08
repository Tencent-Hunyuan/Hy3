# Hy3 API Quickstart

> **5 minutes to first call · 30 minutes to master the key capabilities**

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deploy Hy3](#deploy-hy3)
- [Basic Information](#basic-information)
- [Your First Call](#your-first-call)
- [Parameter Reference](#parameter-reference)
- [Rate Limits](#rate-limits)
- [Common Errors & Fixes](#common-errors--fixes)
- [Next Steps](#next-steps)

---

## Prerequisites

| Requirement | Detail |
|---|---|
| GPU | 8 × NVIDIA H20 (80 GB) or equivalent (total ≥ 640 GB VRAM) |
| Python | 3.10+ |
| OS | Linux (recommended) |
| Network | HuggingFace access to download `tencent/Hy3` weights |

Install the OpenAI Python SDK (used in all examples):

```bash
pip install openai
```

---

## Deploy Hy3

You must start a local inference server before calling the API. Choose either vLLM or SGLang.

### Option A — vLLM (recommended)

```bash
# 1. Install vLLM from source
uv venv --python 3.12 --seed --managed-python
source .venv/bin/activate
git clone https://github.com/vllm-project/vllm.git && cd vllm
uv pip install --editable . --torch-backend=auto

# 2. Start the server
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

### Option B — SGLang

```bash
# 1. Install SGLang from source
git clone https://github.com/sgl-project/sglang && cd sglang
pip install pip --upgrade
pip install "transformers>=5.6.0"
pip install -e "python"

# 2. Start the server
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

Wait until you see `Server started` (or similar) in the logs before proceeding.

---

## Basic Information

| Field | Value |
|---|---|
| **Base URL** | `http://127.0.0.1:8000/v1` |
| **API Key** | `EMPTY` (any non-empty string works for local serving) |
| **Model Name** | `hy3` (set via `--served-model-name` when starting the server) |
| **Chat Endpoint** | `POST /v1/chat/completions` |
| **Context Length** | 256K tokens |
| **Supported Precision** | BF16 |

---

## Your First Call

### cURL

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [{"role": "user", "content": "Hello! Introduce yourself briefly."}],
    "temperature": 0.9,
    "top_p": 1.0
  }'
```

### Python (openai SDK)

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)

response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Hello! Introduce yourself briefly."}],
    temperature=0.9,
    top_p=1.0,
)

print(response.choices[0].message.content)
print(f"\nTokens used: {response.usage.total_tokens}")
```

**Sample output:**
```
Hi! I'm Hy3, a large language model developed by Tencent's Hy Team ...
Tokens used: 87
```

---

## Parameter Reference

### Standard OpenAI Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `model` | string | — | Must match `--served-model-name` (e.g. `hy3`) |
| `messages` | list | — | Conversation history. Each item has `role` and `content` |
| `stream` | bool | `false` | Stream response as SSE chunks |
| `temperature` | float | model default | Randomness. Recommended: `0.9`. Range: [0, 2] |
| `top_p` | float | model default | Nucleus sampling. Recommended: `1.0` |
| `max_tokens` | int | `4096` | Maximum tokens to generate |
| `stop` | list[str] | `null` | Stop generation at these strings |
| `tools` | list | `null` | Function definitions for tool calling |
| `tool_choice` | str/obj | `"auto"` | `"auto"` / `"none"` / `{"type":"function",...}` |

### Hy3-Specific Parameters

Passed via `extra_body={"chat_template_kwargs": {...}}`:

| Parameter | Values | Description |
|---|---|---|
| `reasoning_effort` | `"no_think"` (default) | Direct answer, no chain-of-thought |
| | `"low"` | Brief thinking before answering |
| | `"high"` | Deep chain-of-thought for complex tasks |

**Example — enable deep reasoning:**
```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Prove that √2 is irrational."}],
    temperature=0.9,
    top_p=1.0,
    extra_body={"chat_template_kwargs": {"reasoning_effort": "high"}},
)
```

**When to use each mode:**

| Mode | Use case |
|---|---|
| `no_think` | Chat, summarization, translation, simple Q&A |
| `low` | Light analysis, short code generation |
| `high` | Math proofs, complex coding, multi-step reasoning, agent tasks |

---

## Rate Limits

For **self-hosted** deployments, rate limits depend on your hardware and server configuration — there is no built-in API rate limit. Practical throughput on 8×H20:

| Metric | Approximate value |
|---|---|
| Throughput | ~10–15 tokens/s (speculative decoding enabled) |
| Concurrent requests | Limited by GPU memory and batch size |
| Context length | 256K tokens max |

If you need cloud API access, check [Tencent Cloud TokenHub](https://console.cloud.tencent.com/tokenhub) or [OpenRouter](https://openrouter.ai/tencent/hy3) for their respective rate limit policies.

---

## Common Errors & Fixes

### `Connection refused` / `Failed to connect`

```
httpx.ConnectError: [Errno 111] Connection refused
```

**Cause:** The vLLM/SGLang server is not running or not ready yet.  
**Fix:** Check that the server process is running and has finished loading the model (wait for the "Server started" log line). Verify the port matches (`--port 8000`).

---

### `Model not found` (`NotFoundError`)

```json
{"error": {"message": "The model `hy3` does not exist.", "type": "not_found_error", "code": 404}}
```

**Cause:** The `model` field in your request doesn't match `--served-model-name`.  
**Fix:** Use the exact name you passed to `--served-model-name` when starting the server.

In Python, this raises `openai.NotFoundError` (HTTP 404), not `BadRequestError`:
```python
from openai import NotFoundError
try:
    client.chat.completions.create(model="wrong-name", ...)
except NotFoundError as e:
    print(e.status_code)  # 404
```

---

### `Context length exceeded`

```json
{"error": {"message": "This model's maximum context length is 262144 tokens."}}
```

**Cause:** Your input + max_tokens exceeds 256K.  
**Fix:** Reduce `max_tokens`, shorten your messages, or split the request.

---

### Timeout on long generations

**Cause:** Deep reasoning mode (`reasoning_effort="high"`) with long outputs can take minutes.  
**Fix:** Increase client timeout and use streaming mode:

```python
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    timeout=300,  # 5 minutes
)
# Use stream=True for long outputs to avoid timeout
```

---

### Out of Memory (OOM) on startup

```
torch.cuda.OutOfMemoryError
```

**Cause:** Not enough GPU VRAM to load the full model.  
**Fix:** Hy3 requires ≥8 GPUs with 80 GB VRAM each. For FP8 quantized version use `tencent/Hy3-FP8` (reduces memory footprint).

---

### Tool calls not parsed correctly

**Cause:** Missing `--tool-call-parser hy_v3` (vLLM) or `--tool-call-parser hunyuan` (SGLang) flag.  
**Fix:** Restart the server with the correct parser flag. Also ensure `--enable-auto-tool-choice` is set (vLLM).

---

## Next Steps

Explore the examples in the `examples/` directory:

| File | What it demonstrates |
|---|---|
| [`01_basic_chat.ipynb`](examples/01_basic_chat.ipynb) | Single-turn and multi-turn conversation |
| [`02_streaming.ipynb`](examples/02_streaming.ipynb) | Streaming output with chunk-by-chunk parsing |
| [`03_latency_comparison.ipynb`](examples/03_latency_comparison.ipynb) | Non-streaming vs streaming latency benchmarking |
| [`04_tool_calling.ipynb`](examples/04_tool_calling.ipynb) | Function calling (single + multi-turn tool loop) |
| [`05_reasoning_mode.ipynb`](examples/05_reasoning_mode.ipynb) | Comparing `no_think` / `low` / `high` reasoning modes |
| [`06_error_handling.ipynb`](examples/06_error_handling.ipynb) | Retry logic for timeouts, rate limits, and network errors |

For deployment details, see the [vLLM recipes](https://recipes.vllm.ai/tencent/Hy3) and [SGLang cookbook](https://lmsysorg.mintlify.app/cookbook/autoregressive/Tencent/Hy3).
