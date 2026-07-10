# Hy3 API examples

[简体中文](README_CN.md) · [API quickstart](../../quickstart.md) · [Project README](../../README.md)

## Setup

Run these commands from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r examples/api/requirements.txt
cp examples/api/.env.example examples/api/.env
```

On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1` and copy the template with `Copy-Item examples/api/.env.example examples/api/.env`.

Start from the self-hosted defaults in `.env.example`, or configure OpenRouter as described in the [API quickstart](../../quickstart.md#api-configuration). Do not commit a real API key.

## Environment variables

| Variable | Self-hosted default | OpenRouter |
|---|---|---|
| `HY3_BACKEND` | `self_hosted` | `openrouter` |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | `https://openrouter.ai/api/v1` |
| `HY3_API_KEY` | `EMPTY` | Read from your environment |
| `HY3_MODEL` | `hy3` | `tencent/hy3:free` |
| `HY3_TIMEOUT` | `120` | A finite positive number |

`common.py` loads `examples/api/.env`, validates these values, constructs the OpenAI client, maps reasoning configuration, and normalizes response fields shared by the examples.

## Learning path

Run each script from the repository root. The guides contain complete requests, response parsing, deterministic offline output, and limitations.

| Step | Script | Guide | What it teaches |
|---|---|---|---|
| 1 | [`01_basic_chat.py`](01_basic_chat.py) | [Basic chat](01_basic_chat.md) / [中文](01_basic_chat_CN.md) | Single-turn request, assistant history, and normalized response fields. |
| 2 | [`02_streaming.py`](02_streaming.py) | [Streaming](02_streaming.md) / [中文](02_streaming_CN.md) | Empty chunks, usage-only chunks, content/reasoning separation, and fragmented tool calls. |
| 3 | [`03_streaming_vs_non_streaming.py`](03_streaming_vs_non_streaming.py) | [Streaming versus non-streaming](03_streaming_vs_non_streaming.md) / [中文](03_streaming_vs_non_streaming_CN.md) | First output, first visible content, and total timing with identical sampling. |
| 4 | [`04_tool_calling.py`](04_tool_calling.py) | [Tool calling](04_tool_calling.md) / [中文](04_tool_calling_CN.md) | Multiple calls in one assistant turn, sequential execution, assistant/tool history, structured errors, and bounded rounds. |
| 5 | [`05_reasoning_mode.py`](05_reasoning_mode.py) | [Reasoning mode](05_reasoning_mode.md) / [中文](05_reasoning_mode_CN.md) | Same-question comparison of `no_think` and `high` with backend mapping. |
| 6 | [`06_error_handling_retry.py`](06_error_handling_retry.py) | [Error handling and retry](06_error_handling_retry.md) / [中文](06_error_handling_retry_CN.md) | SDK retry disabling, application retry policy, Retry-After, jitter, and offline simulation. |

Commands:

```bash
python examples/api/01_basic_chat.py
python examples/api/02_streaming.py
python examples/api/03_streaming_vs_non_streaming.py --warmup
python examples/api/04_tool_calling.py
python examples/api/05_reasoning_mode.py
python examples/api/06_error_handling_retry.py --simulate
```

The first five commands and retry script without `--simulate` require a configured backend. The simulation is deterministic and needs neither API configuration nor network access.
