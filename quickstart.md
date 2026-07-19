# Hy3 API Quickstart

This guide helps you make your first Hy3 API call within **5 minutes** and get familiar with the main capabilities within **30 minutes**.

Hy3 exposes an **OpenAI-compatible** Chat Completions API. You can reuse the `openai` Python SDK, `curl`, or any OpenAI-compatible client.

Two ways to call Hy3:

| Path | Who it is for | Base URL |
|:---|:---|:---|
| **A. Tencent Cloud TokenHub (recommended for first call)** | No local GPU; create an API key and go | `https://tokenhub.tencentmaas.com/v1` |
| **B. Self-hosted vLLM / SGLang** | Full control, offline / private deploy | `http://127.0.0.1:8000/v1` (default) |

Runnable examples (`.py` / `.md` / `.ipynb`, bilingual): see [`examples/en/`](./examples/en/) and [`examples/cn/`](./examples/cn/).

---

## Table of Contents

- [1. Basic Information](#1-basic-information)
- [2. Minimal Runnable Example (5 minutes)](#2-minimal-runnable-example-5-minutes)
- [3. Parameter Reference](#3-parameter-reference)
- [4. Troubleshooting Common Errors](#4-troubleshooting-common-errors)
- [5. Next Steps](#5-next-steps)

---

## 1. Basic Information

### 1.1 Hosted API — TokenHub

| Item | Value | Description |
|:---|:---|:---|
| Base URL | `https://tokenhub.tencentmaas.com/v1` | OpenAI-compatible endpoint |
| API Key | Your TokenHub key | Create / manage in the TokenHub console; **never commit keys** |
| Model (`model`) | `hy3` | Use exactly `hy3` unless the console shows another served name |
| Protocol | OpenAI Chat Completions | `/v1/chat/completions` |
| Context length | 256K | Input + output tokens per request |

**Rate limits (hosted):** QPS / TPM / concurrency are configured by the cloud product. On HTTP `429`, back off (prefer `Retry-After` when present) and reduce concurrency. See the provider quota docs for exact numbers.

### 1.2 Self-hosted — vLLM / SGLang

| Item | Value | Description |
|:---|:---|:---|
| Base URL | `http://127.0.0.1:8000/v1` | Default local listen address + `/v1` |
| API Key | `EMPTY` | Local deploy typically does not validate keys; any non-empty string works |
| Model (`model`) | `hy3` | Must match `--served-model-name hy3` |
| Hardware | 8× GPU (H20-3e recommended) | 295B MoE needs large VRAM |
| Tool parser | vLLM: `hy_v3` / SGLang: `hunyuan` | Required for tool calling |
| Reasoning parser | vLLM: `hy_v3` / SGLang: `hunyuan` | Required to expose `reasoning_content` |

**Rate limits (local):** no unified hard limit. Effective concurrency is set by vLLM/SGLang (KV cache, `--max-num-seqs`, GPU memory). Long 256K contexts reduce concurrent capacity.

### 1.3 Environment variables used by examples

| Variable | Default | Description |
|:---|:---|:---|
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI-compatible base URL |
| `HY3_API_KEY` | `EMPTY` | API key |
| `HY3_MODEL` | `hy3` | Model name |
| `HY3_TIMEOUT` | `120` | Client timeout (seconds) |

Copy [`examples/.env.example`](./examples/.env.example) as a template. Do not commit real keys.

---

## 2. Minimal Runnable Example (5 minutes)

### 2.1 Path A — TokenHub (no local GPU)

```bash
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
export HY3_API_KEY="sk-xxxxxxxx"   # replace with your key
export HY3_MODEL="hy3"
```

**curl**

```bash
curl -X POST "$HY3_BASE_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HY3_API_KEY" \
  -d '{
    "model": "hy3",
    "messages": [
      {"role": "user", "content": "用一句话介绍一下你自己。"}
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "thinking": {"type": "disabled"},
    "chat_template_kwargs": {"reasoning_effort": "no_think"}
  }'
```

**Python (OpenAI SDK)**

```bash
pip install openai
```

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "https://tokenhub.tencentmaas.com/v1"),
    api_key=os.environ["HY3_API_KEY"],  # required on TokenHub
)

response = client.chat.completions.create(
    model=os.environ.get("HY3_MODEL", "hy3"),
    messages=[{"role": "user", "content": "用一句话介绍一下你自己。"}],
    temperature=0.9,
    top_p=1.0,
    # Dual-compatible thinking switch (cloud + local):
    extra_body={
        "thinking": {"type": "disabled"},  # TokenHub
        "chat_template_kwargs": {"reasoning_effort": "no_think"},  # vLLM / SGLang
    },
)

print(response.choices[0].message.content)
```

Expected response shape (content is model-generated):

```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "model": "hy3",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "我是 Hy3，由腾讯混元团队开发的……"},
      "finish_reason": "stop"
    }
  ],
  "usage": {"prompt_tokens": 12, "completion_tokens": 28, "total_tokens": 40}
}
```

### 2.2 Path B — Local vLLM / SGLang

1. Start the server per the [Deployment](./README.md#deployment) section of the README (`--served-model-name hy3`, port `8000`).
2. Confirm: `curl http://127.0.0.1:8000/v1/models`
3. Call with `base_url=http://127.0.0.1:8000/v1` and `api_key="EMPTY"`.

```python
from openai import OpenAI

client = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="EMPTY")
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "用一句话介绍一下你自己。"}],
    temperature=0.9,
    top_p=1.0,
    extra_body={
        "thinking": {"type": "disabled"},
        "chat_template_kwargs": {"reasoning_effort": "no_think"},
    },
)
print(response.choices[0].message.content)
```

> **SDK note:** with the OpenAI Python SDK, vendor fields go in `extra_body`. With raw `curl`/HTTP, put `thinking` and `chat_template_kwargs` at the top level of the JSON body.

---

## 3. Parameter Reference

### 3.1 temperature

| Field | Content |
|:---|:---|
| Meaning | Sampling randomness. Higher → more diverse; lower → more deterministic. |
| Range | `0.0` ~ `2.0` |
| Recommended | **`0.9`** (Hy3 official recommendation) |

### 3.2 top_p

| Field | Content |
|:---|:---|
| Meaning | Nucleus sampling threshold. |
| Range | `0.0` ~ `1.0` |
| Recommended | **`1.0`** |

### 3.3 max_tokens

| Field | Content |
|:---|:---|
| Meaning | Max generated tokens (excluding input). |
| Range | Up to context length minus input (256K total) |
| Recommended | Chat 512~2048; long form 4096~8192; `high` thinking ≥ 8192 |

### 3.4 stop

| Field | Content |
|:---|:---|
| Meaning | Stop sequences; generation halts on match. |
| Type | string or array of strings |

### 3.5 tools (Tool Calling)

Declare tools with the OpenAI `tools` JSON Schema. The model may return `tool_calls`; your client executes them and feeds `role=tool` results back.

**Self-hosted must enable the tool-call parser:**

- vLLM: `--tool-call-parser hy_v3 --reasoning-parser hy_v3 --enable-auto-tool-choice`
- SGLang: `--tool-call-parser hunyuan --reasoning-parser hunyuan`

See [`examples/en/04_tool_calling.py`](./examples/en/04_tool_calling.py) for a bounded multi-turn tool loop.

### 3.6 Thinking / reasoning switch

Hy3 supports thinking depth. **Send both forms** so the same code works on TokenHub and local:

| Mode | TokenHub (`thinking.type`) | Local (`reasoning_effort`) | Use when |
|:---|:---|:---|:---|
| Off | `disabled` | `no_think` | Everyday chat, lowest latency |
| Low | `enabled` | `low` | Light structure / multi-constraint |
| High | `enabled` | `high` | Math, code, hard reasoning |

```python
extra_body = {
    "thinking": {"type": "enabled"},  # TokenHub
    "chat_template_kwargs": {"reasoning_effort": "high"},  # local
}
# When enabled, CoT may appear in message.reasoning_content
# (local needs --reasoning-parser; TokenHub separates it server-side).
```

Full comparison: [`examples/en/05_reasoning_mode.py`](./examples/en/05_reasoning_mode.py).

---

## 4. Troubleshooting Common Errors

### 4.1 Connection failure

**Symptom:** `Connection refused` / `Failed to connect`.

- TokenHub: check network / proxy / DNS; verify base URL.
- Local: service not up, wrong port, or model still loading. Check startup logs and `curl .../v1/models`.

### 4.2 Authentication failure (401)

- TokenHub: empty / wrong / expired API key; ensure `Authorization: Bearer <key>`.
- Local: use any non-empty key (e.g. `EMPTY`); avoid `api_key=None`.

### 4.3 Model not found (404 / 400)

- Request `model` must match served name (`hy3`).
- List models: `GET {base_url}/models`.

### 4.4 Timeout

- Raise client `timeout` (examples default 120s).
- `high` thinking and long contexts need more time and larger `max_tokens`.
- Lower concurrency if the server is queueing.

### 4.5 Rate limit (429)

- Back off with exponential delay; honor `Retry-After` when present.
- Lower client concurrency; for cloud, check quota.
- Example: [`examples/en/06_error_handling_retry.py`](./examples/en/06_error_handling_retry.py).

### 4.6 Empty `reasoning_content` when thinking is on

- TokenHub: ensure `thinking: {type: enabled}` is sent.
- Local vLLM: `--reasoning-parser hy_v3`
- Local SGLang: `--reasoning-parser hunyuan`

### 4.7 Tool call not triggered

**Symptom:** `message.tool_calls` is `None` even though `tools` was sent.

- Local vLLM: start with `--tool-call-parser hy_v3 --enable-auto-tool-choice`.
- Local SGLang: start with `--tool-call-parser hunyuan`.
- Ensure `tool_choice` is `auto` (or a specific tool); `"none"` disables tool calls.
- Some chat templates require `tools` to be passed via `extra_body` rather than top-level — check the server's doc if unsure.
- Example: [`examples/en/04_tool_calling.py`](./examples/en/04_tool_calling.py).

### 4.8 Chat template missing / malformed

**Symptom:** `Chat template not set` / `Apply chat template failed` / garbled output.

- The served model dir must contain a valid `chat_template.jinja` (or tokenizer config with one).
- If you load weights from a custom path, re-check the tokenizer files are present.
- For thinking mode, the template must support `reasoning_effort` — otherwise `reasoning_content` stays empty.
- Avoid manually concatenating prompts; always go through the `messages` API.

### 4.9 CUDA out-of-memory (local deployment)

**Symptom:** Server log `CUDA out of memory` / request returns 500 / hang.

- Hy3 needs 8 GPUs (e.g. H20-3e); a single 24GB card cannot serve it.
- Lower `--max-model-len` / `--max-num-seqs` / `gpu-memory-utilization`.
- Close other GPU processes (`nvidia-smi`); TP=8 is mandatory for full weights.
- Try quantization (if provided) or switch to the cloud TokenHub API if GPU is insufficient.
- For long-context requests, raise `max_tokens` cautiously — output also consumes KV cache.

---

## 5. Next Steps

| Goal | Link |
|:---|:---|
| English examples (py / md / ipynb) | [`examples/en/`](./examples/en/) |
| Chinese examples | [`examples/cn/`](./examples/cn/) |
| Shared helpers + offline tests | [`examples/common.py`](./examples/common.py), [`examples/tests/`](./examples/tests/) |
| Full deployment (vLLM / SGLang) | [README Deployment](./README.md#deployment) |
| Fine-tuning | [`finetune/README.md`](./finetune/README.md) |
| Chinese quickstart | [`quickstart_CN.md`](./quickstart_CN.md) |

```bash
pip install -r examples/requirements.txt
# optional offline tests (no API key):
pip install -r examples/requirements-dev.txt
pytest examples/tests -q
```

Feedback: `hunyuan_opensource@tencent.com`.
