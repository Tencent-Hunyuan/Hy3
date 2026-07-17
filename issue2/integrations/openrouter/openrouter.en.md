# Using Hy3 with OpenRouter

> 🌐 中文版本： [openrouter.md](openrouter.md)

## Introduction

[OpenRouter](https://openrouter.ai) is a unified LLM API gateway that aggregates 200+ models. Its key advantage is that you **don't need to run your own GPU service** — everything is billed on a pay-as-you-go basis, and a single API Key gives you access to all models, including Hy3.

## Use Cases

- Zero-deploy, instant Hy3 experience
- Switching and comparing across multiple models (A/B testing)
- Individual developers who don't want to maintain a GPU cluster

## Requirements

| Item | Requirement |
|:---|:---|
| OpenRouter account | Free registration |
| API Key | Create one on the [Keys page](https://openrouter.ai/keys) |
| Balance | Pay per model usage (Hy3 is around the $0.50/M tokens tier) |
| Client | Any client that supports the OpenAI API |

## Configuration

### Generic client config (Python / Node.js / any OpenAI SDK)

```
base_url    = "https://openrouter.ai/api/v1"
api_key     = "sk-or-v1-your-openrouter-key"
model       = "tencent/hy3"              # Note: NOT "hy3"
```

### Key parameter mapping

| Native Hy3 param | How to use it on OpenRouter |
|:---|:---|
| `reasoning_effort` | Pass through via `extra_body` or `provider.preferences` |
| `temperature` | Pass through directly, recommended `0.9` |
| `top_p` | Pass through directly, recommended `1.0` |
| `max_tokens` | Limits the response length |

## End-to-End Demo

### Python example: calling Hy3 for deep reasoning

```python
import requests
import json

API_KEY = "sk-or-v1-your-key"
BASE_URL = "https://openrouter.ai/api/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": "tencent/hy3",
    "messages": [
        {
            "role": "user",
            "content": "Implement a thread-safe LRU cache in Rust, with detailed comments and unit tests."
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 4096,
    # Enable deep reasoning mode
    "extra_body": {
        "chat_template_kwargs": {"reasoning_effort": "high"}
    }
}

response = requests.post(
    f"{BASE_URL}/chat/completions",
    headers=headers,
    json=payload,
    timeout=120
)

print(response.json()["choices"][0]["message"]["content"])
```

### One-line cURL test in the terminal

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer sk-or-v1-your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tencent/hy3",
    "messages": [{"role": "user", "content": "Introduce yourself in one sentence"}],
    "temperature": 0.9,
    "top_p": 1.0,
    "extra_body": {"chat_template_kwargs": {"reasoning_effort": "no_think"}}
  }'
```

### Expected output

```
I am Tencent Hunyuan Hy3, a 295B-parameter Mixture-of-Experts (MoE) large language model,
skilled at reasoning, coding, long-text processing, and Agent tasks.
```

## Common Notes

| Issue | Cause | Solution |
|:---|:---|:---|
| `model not found` | Wrong model ID | Make sure you use `tencent/hy3`, not `hy3` |
| `provider error` | Hy3 unavailable on OpenRouter | Log in to OpenRouter and check Hy3 status |
| `401 Unauthorized` | Misspelled API Key or missing prefix | Ensure you use the full `sk-or-v1-xxx` format |
| Long reasoning time | `reasoning_effort=high` generates a chain-of-thought | Use `no_think` for simple tasks |
| `max_tokens` truncation | Response gets cut off | Increase `max_tokens` or leave it unset (4096+ recommended) |
| High cost | Hy3 is billed per token on OpenRouter | Monitor usage, use `no_think` to reduce consumption |


[← Back to Index](../README.en.md)
