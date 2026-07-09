# Hy3 Example Code (English)

This directory provides a set of ready-to-run Python examples that demonstrate how to call a locally deployed Tencent Hunyuan Hy3 model (vLLM / SGLang) via the OpenAI-compatible API.

This is the English edition of the examples. The code logic, variable names, and model-facing prompts are kept identical to the Chinese edition under `examples/`; only the comments, docstrings, terminal-print labels, and documentation prose are translated into English.

All examples read connection info from environment variables, default to the local service `http://127.0.0.1:8000/v1`, and use the fixed model name `hy3`.

## Example List

| Example | Description |
| --- | --- |
| `01_basic_chat` | Single-turn / multi-turn chat |
| `02_streaming` | Streaming request + per-chunk parsing |
| `03_nonstream_vs_stream` | Non-streaming vs streaming comparison (TTFT / total latency) |
| `04_tool_calling` | One tool call + multi-turn tool loop |
| `05_reasoning_mode` | Reasoning on / off comparison |
| `06_error_handling_retry` | Retry and backoff for timeout / rate limit / network errors |

## Prerequisites

- Python 3.8+
- Install the OpenAI SDK:

  ```bash
  pip install openai
  ```

- Running `06_error_handling_retry` also requires `tenacity`:

  ```bash
  pip install tenacity
  ```

- **A running Hy3 service must be started first** (vLLM or SGLang). For deployment instructions, see the [Deployment](../../README.md#deployment) section of the root README (vLLM / SGLang launch commands). The default service address is `http://127.0.0.1:8000/v1`.

## Environment Variables

All examples read connection info from the following environment variables, falling back to defaults when unset:

| Environment variable | Default | Description |
| --- | --- | --- |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI-compatible API address of the Hy3 service |
| `HY3_API_KEY` | `EMPTY` | API key; any value works for a local deployment |

Bash example (Linux / macOS):

```bash
# Use the default local service
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"

# To point to a remote host or a custom port
# export HY3_BASE_URL="http://10.0.0.10:8000/v1"
# export HY3_API_KEY="sk-xxxxxx"
```

Windows PowerShell example:

```powershell
$env:HY3_BASE_URL = "http://127.0.0.1:8000/v1"
$env:HY3_API_KEY = "EMPTY"
```

## How to Run

Run from the repository root (recommended), or from inside the `examples/` directory:

```bash
python examples/en/01_basic_chat.py
python examples/en/02_streaming.py
python examples/en/03_nonstream_vs_stream.py
python examples/en/04_tool_calling.py
python examples/en/05_reasoning_mode.py
python examples/en/06_error_handling_retry.py
```

Each example is accompanied by a `.md` doc of the same name (English), containing the complete request code, response parsing, and a sample output.
