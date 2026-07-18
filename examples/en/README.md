# Hy3 Example Code (English)

Ready-to-run examples for calling Tencent Hunyuan **Hy3** via the OpenAI-compatible API.

Works with:

- **Tencent Cloud TokenHub** — set `HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1` and your API key
- **Local vLLM / SGLang** — defaults to `http://127.0.0.1:8000/v1`, `api_key=EMPTY`

Each example ships as **`.py` + `.md` + `.ipynb`**. Shared helpers live in [`../common.py`](../common.py). Chinese docs/scripts: [`../cn/`](../cn/).

## Example list

| Example | Description | Files |
| --- | --- | --- |
| `01_basic_chat` | Single-turn / multi-turn chat | [py](01_basic_chat.py) · [md](01_basic_chat.md) · [ipynb](01_basic_chat.ipynb) |
| `02_streaming` | Streaming + per-chunk parse | [py](02_streaming.py) · [md](02_streaming.md) · [ipynb](02_streaming.ipynb) |
| `03_nonstream_vs_stream` | TTFT / total latency comparison | [py](03_nonstream_vs_stream.py) · [md](03_nonstream_vs_stream.md) · [ipynb](03_nonstream_vs_stream.ipynb) |
| `04_tool_calling` | One tool call + bounded multi-turn loop | [py](04_tool_calling.py) · [md](04_tool_calling.md) · [ipynb](04_tool_calling.ipynb) |
| `05_reasoning_mode` | `no_think` / `low` / `high` comparison | [py](05_reasoning_mode.py) · [md](05_reasoning_mode.md) · [ipynb](05_reasoning_mode.ipynb) |
| `06_error_handling_retry` | Timeout / 429 / network retry + backoff | [py](06_error_handling_retry.py) · [md](06_error_handling_retry.md) · [ipynb](06_error_handling_retry.ipynb) |

Every `.md` includes: **full request code** + **response parsing** + **sample output**.

## Prerequisites

```bash
pip install -r examples/requirements.txt
```

For offline unit tests (no API key):

```bash
pip install -r examples/requirements-dev.txt
pytest examples/tests -q
```

- **TokenHub:** create an API key; no GPU required.
- **Local:** start Hy3 with vLLM or SGLang first (see root [README Deployment](../../README.md#deployment)). For tool calling / reasoning fields, enable the parsers noted in the quickstart.

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI-compatible API base |
| `HY3_API_KEY` | `EMPTY` | API key |
| `HY3_MODEL` | `hy3` | Model name |
| `HY3_TIMEOUT` | `120` | Client timeout (seconds) |

Template: [`../.env.example`](../.env.example).

```bash
# Local
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_API_KEY="EMPTY"

# TokenHub
# export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
# export HY3_API_KEY="sk-xxxxxxxx"
```

Windows PowerShell:

```powershell
$env:HY3_BASE_URL = "http://127.0.0.1:8000/v1"
$env:HY3_API_KEY = "EMPTY"
```

## How to run

From the repository root:

```bash
python examples/en/01_basic_chat.py
python examples/en/02_streaming.py
python examples/en/03_nonstream_vs_stream.py
python examples/en/04_tool_calling.py
python examples/en/05_reasoning_mode.py
python examples/en/06_error_handling_retry.py
```

Or open the matching `.ipynb` in Jupyter / VS Code.

## Design notes

- **Dual-compatible thinking switch:** examples send both TokenHub `thinking` and local `chat_template_kwargs.reasoning_effort` (via `common.build_extra_body`).
- **Bounded tool loop & retries:** max iterations / max attempts / max total wait so demos never hang.
- **No secrets in repo:** keys only via env; sample outputs are representative / redacted.

See also: [quickstart.md](../../quickstart.md).
