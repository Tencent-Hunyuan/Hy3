# Hy3 API Quickstart

5-minute first call, 30-minute master key capabilities.

---

## Overview

| Item | Description |
|------|-------------|
| **Base URL** | `https://tokenhub.tencentmaas.com/v1` (China) / `https://tokenhub-intl.tencentmaas.com/v1` (Global) |
| **API Key** | Create at [TokenHub Console](https://console.cloud.tencent.com/tokenhub), format `sk-xxx` |
| **Model Name** | `hy3` / `hy3-preview` |
| **Context Length** | 256K tokens (192K max input, 128K max output) |
| **Protocol** | OpenAI Chat Completions API compatible |
| **Self-hosted** | Deploy via [vLLM](https://recipes.vllm.ai/tencent/Hy3) or [SGLang](https://lmsysorg.mintlify.app/cookbook/autoregressive/Tencent/Hy3) |

### Rate Limits

| Tier | Limit |
|------|-------|
| Default | Dynamic adjustment based on TokenHub plan tier (Lite < Standard < Pro < Max) |
| Over-limit | HTTP 429 `tpm rate limit exceeded` |

### Pricing (Pay-as-you-go, ¥/M tokens)

| Model | Input | Output | Cache Hit |
|-------|-------|--------|-----------|
| hy3 | ¥1.00 | ¥4.00 | ¥0.25 |
| hy3-preview | ¥1.20 | ¥4.00 | ¥0.40 |

---

## Prerequisites

1. Register a [Tencent Cloud account](https://cloud.tencent.com) and complete identity verification
2. Activate [TokenHub](https://console.cloud.tencent.com/tokenhub)
3. Create an API Key at [API Key Management](https://console.cloud.tencent.com/tokenhub/apikey)
4. Set environment variables (recommended):

```bash
export HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
export HY3_API_KEY="sk-xxxxxxxxxxxxxxxx"
export HY3_MODEL=hy3
```

Or copy and edit `.env`:

```bash
cp .env.example .env
# Edit .env with your API endpoint and key
pip install -r requirements.txt
python api/examples/01_basic_chat/basic_chat.py
```

---

## Minimal Runnable Examples

### cURL

```bash
curl https://tokenhub.tencentmaas.com/v1/chat/completions \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "Hello! Can you briefly introduce yourself?"}
    ],
    "temperature": 0.9,
    "top_p": 1.0
  }'
```

### Python + OpenAI SDK

```bash
pip install openai python-dotenv
```

```python
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("HY3_API_KEY", "EMPTY"),
    base_url=os.getenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
)

response = client.chat.completions.create(
    model=os.getenv("HY3_MODEL", "hy3"),
    messages=[
        {"role": "user", "content": "Hello! Can you briefly introduce yourself?"},
    ],
    temperature=0.9,
    top_p=1.0,
)

print(response.choices[0].message.content)
```

---

## Parameter Reference

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `model` | string | — | `hy3`, `hy3-preview` | Model identifier |
| `messages` | array | — | — | Conversation messages (system / user / assistant / tool) |
| `temperature` | float | 1.0 | 0.0 – 2.0 | Sampling temperature; higher = more random |
| `top_p` | float | 1.0 | 0.0 – 1.0 | Nucleus sampling probability threshold |
| `max_tokens` | int | — | 1 – 131072 | Max output tokens |
| `stream` | bool | false | — | Enable SSE streaming |
| `stop` | string/array | — | — | Stop sequences, max 4 |
| `tools` | array | — | — | Tool/function definitions |
| `tool_choice` | string/object | `"auto"` | `"auto"` / `"none"` / `"required"` | Tool calling strategy |
| `seed` | int | — | 1 – 10000 | Random seed for reproducibility |
| `reasoning_effort` | string | `"no_think"` | `"no_think"` / `"low"` / `"medium"` / `"high"` | Reasoning mode, via `extra_body` |

### Reasoning Mode

`reasoning_effort` is passed via `extra_body`:

```python
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "..."}],
    extra_body={
        "chat_template_kwargs": {
            "reasoning_effort": "high"
        }
    },
)
```

| Value | Use Case |
|-------|----------|
| `"no_think"` | Default. Direct response for everyday chat, simple Q&A |
| `"low"` | Light reasoning for simple logic tasks |
| `"medium"` | Moderate reasoning, balances speed and depth |
| `"high"` | Deep thinking (full CoT) for math, coding, complex reasoning |

---

## Common Error Troubleshooting

| HTTP Status | Error | Cause | Solution |
|-------------|-------|-------|----------|
| 401 | `Unauthorized` | Invalid/missing API Key | Check `Authorization` header: `Bearer sk-...` |
| 403 | `Forbidden` | Service not activated or insufficient balance | Activate TokenHub and top up |
| 429 | `tpm rate limit exceeded` | Rate limit exceeded | Reduce concurrency or upgrade plan; implement exponential backoff |
| 429 | `insufficient quota` | Quota exhausted | Check plan or switch to pay-as-you-go |
| 400 | `invalid model` | Wrong model name | Use `hy3` or `hy3-preview` |
| 400 | `invalid messages format` | Invalid message format | Ensure messages is valid JSON array, roles are correct |
| 408/504 | `Request timed out` | Request timeout | Increase timeout or check network |
| 500 | `Internal Server Error` | Server-side error | Retry later; contact support if persistent |

---

## Next Steps

See the [examples](./examples) directory for complete runnable demos:

| Example | Description |
|---------|-------------|
| [01 - Basic Chat](./examples/01_basic_chat) | Single-turn / multi-turn conversation |
| [02 - Streaming](./examples/02_streaming) | SSE streaming and chunk-by-chunk parsing |
| [03 - Non-streaming vs Streaming](./examples/03_nonstreaming_vs_streaming) | First-token latency & total time comparison |
| [04 - Tool Calling](./examples/04_tool_calling) | Single call + multi-round tool loop |
| [05 - Reasoning Mode](./examples/05_reasoning_mode) | Reasoning on/off comparison |
| [06 - Error Handling & Retry](./examples/06_error_handling_retry) | Timeout / rate-limit / network retry with backoff |

---

## Reference Links

- [TokenHub API Documentation](https://cloud.tencent.com/document/product/1823/130078)
- [Hy3 TokenHub Guide](https://cloud.tencent.com/document/product/1823/132252)
- [Pricing Details](https://cloud.tencent.com/document/product/1823/130055)
- [TokenHub Console](https://console.cloud.tencent.com/tokenhub)
