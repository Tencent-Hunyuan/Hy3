<p align="left">
   <a href="quickstart_CN.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>
# Hy3 API Quickstart Guide

> **Goal**: Make your first successful API call within **5 minutes** and master core features in **30 minutes**.

---

## 1. Prerequisites

| Requirement | Details |
|---|---|
| Python | >= 3.9 |
| openai SDK | `pip install openai>=1.30.0` |
| Hardware (self-hosted) | 8x high-memory GPUs (H20-3e or better) |
| Serving engine | [vLLM](https://github.com/vllm-project/vllm) or [SGLang](https://github.com/sgl-project/sglang) |

---

## 2. API Basics

### Endpoint

```
POST http://<host>:<port>/v1/chat/completions
```

### Model Identifier

| Model | Description |
|---|---|
| `hy3` | Hy3 full model (295B MoE, 21B active) |
| `Hy3-FP8` | FP8 quantized variant (lower VRAM) |

### Authentication

For **self-hosted** deployments, use any non-empty string as the API key:

```
Authorization: Bearer EMPTY
```

For **cloud-hosted** services (e.g., Tencent Cloud Hunyuan, OpenRouter), use the API key provided by the platform.

### Rate Limits

Self-hosted deployments have no built-in rate limits; throughput depends on GPU resources. Cloud providers may impose per-minute or per-day quotas -- consult your provider's documentation.

---

## 3. Your First API Call (5 minutes)

### Option A: curl

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer EMPTY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "What is Hy3?"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 512
  }'
```

**Expected Response:**

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1720000000,
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hy3 is a 295-billion parameter Mixture-of-Experts (MoE) model developed by Tencent...",
        "reasoning_content": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 156,
    "total_tokens": 168
  }
}
```

### Option B: Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",  # any non-empty string for self-hosted
)

response = client.chat.completions.create(
    model="hy3",
    messages=[
        {"role": "user", "content": "What is Hy3?"}
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
)

print(response.choices[0].message.content)
```

---

## 4. Core Parameters

### Generation Control

| Parameter | Type | Default | Description |
|---|---|---|---|
| `temperature` | float | 0.9 | Sampling temperature. Higher = more creative. Range: 0.0 - 2.0 |
| `top_p` | float | 1.0 | Nucleus sampling. Lower = more focused. Range: 0.0 - 1.0 |
| `max_tokens` | int | None | Maximum number of tokens to generate. Model context: 256K tokens |
| `stop` | str / list | None | Stop sequences. Up to 4 sequences supported |

> **Recommended**: Use `temperature=0.9`, `top_p=1.0` for general use. For deterministic outputs, set `temperature=0.0`.

### Reasoning Mode (Deep Thinking)

Hy3 supports configurable reasoning depth. When enabled, the response includes a `reasoning_content` field showing the model's thinking process.

**Cloud API** (e.g., Tencent TokenHub, OpenRouter):

```python
extra_body={"reasoning_effort": "high"}  # "no_think" | "low" | "high"
```

**Self-hosted** (vLLM / SGLang):

```python
extra_body={
    "chat_template_kwargs": {
        "reasoning_effort": "high"  # "no_think" | "low" | "high"
    }
}
```

| Level | Use Case |
|---|---|
| `"no_think"` | Direct responses, simple Q&A (default) |
| `"low"` | Light reasoning, basic logic tasks |
| `"high"` | Deep chain-of-thought for complex math, coding, analysis |

When reasoning is enabled, the response includes a `reasoning_content` field showing the model's thinking process.

### Tool Calling (Function Calling)

Requires server-side configuration:

**vLLM:**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model tencent/Hy3 \
  --tool-call-parser hy_v3 \
  --enable-auto-tool-choice
```

**SGLang:**
```bash
python -m sglang.launch_server \
  --model tencent/Hy3 \
  --tool-call-parser hunyuan
```

---

## 5. Streaming Responses

Enable real-time token streaming for lower latency:

```python
stream = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "Explain quantum computing"}],
    temperature=0.9,
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

---

## 6. Examples Index

| # | Topic | File | Description |
|---|---|---|---|
| 01 | Basic Chat | [01_basic_chat.py](./examples/01_basic_chat.py) | Single-turn and multi-turn conversations |
| 02 | Streaming | [02_streaming.py](./examples/02_streaming.py) | Stream requests with chunk processing |
| 03 | Latency Compare | [03_latency_compare.py](./examples/03_latency_compare.py) | Streaming vs non-streaming performance |
| 04 | Tool Calling | [04_tool_calling.py](./examples/04_tool_calling.py) | Function calling with multi-turn loops |
| 05 | Reasoning Mode | [05_reasoning_mode.py](./examples/05_reasoning_mode.py) | Reasoning on/off comparison |
| 06 | Error Handling | [06_error_handling.py](./examples/06_error_handling.py) | Retry, backoff, and resilience patterns |

---

## 7. Troubleshooting

### CUDA Out of Memory (OOM)

**Symptom:** Server crashes with `CUDA out of memory` error.

**Solutions:**
1. Use `Hy3-FP8` instead of the full model to reduce VRAM usage.
2. Reduce `--max-model-len` in vLLM/SGLang startup arguments.
3. Enable tensor parallelism with `--tensor-parallel-size 8`.

### Client Timeout

**Symptom:** Request times out before receiving a response.

**Solutions:**
1. Increase client-side timeout: `client = OpenAI(timeout=300)`.
2. Use streaming mode to receive tokens incrementally.
3. Reduce `max_tokens` in your request.

### Empty or Garbled Response

**Symptom:** Response content is empty or nonsensical.

**Solutions:**
1. Verify the model is fully loaded before sending requests.
2. Check that `temperature` is within [0.0, 2.0].
3. Ensure the server's `--tool-call-parser` matches your tool calling format.

### Connection Refused

**Symptom:** `ConnectionError: [Errno 111] Connection refused`

**Solutions:**
1. Verify the server is running: `curl http://127.0.0.1:8000/health`.
2. Check firewall rules for the configured port.
3. Ensure `--host 0.0.0.0` is set if accessing from another machine.

---

## 8. Configuration via Environment Variables

All examples support environment variable configuration for flexible deployment:

| Variable | Default | Description |
|---|---|---|
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | API endpoint |
| `HY3_API_KEY` | `EMPTY` | API key |
| `HY3_MODEL` | `hy3` | Model identifier |

Copy [`.env.example`](../.env.example) to `.env` and fill in your values:

```bash
cp .env.example .env
# Edit .env with your configuration
```

---

## 9. Further Resources

- [Hy3 GitHub Repository](https://github.com/Tencent-Hunyuan/Hy3)
- [vLLM Documentation](https://docs.vllm.ai/)
- [SGLang Documentation](https://sgl-project.github.io/)
- [OpenAI Python SDK Reference](https://platform.openai.com/docs/api-reference)
