# Hy3 API Examples

Runnable examples for the OpenAI-compatible Hy3 Chat Completions API.

| Language | Path |
|:---|:---|
| English | [`en/`](./en/) |
| 中文 | [`cn/`](./cn/) |

Each of the 6 topics ships as **`.py` + `.md` + `.ipynb`**:

1. `01_basic_chat` — single / multi-turn  
2. `02_streaming` — stream + chunk parse  
3. `03_nonstream_vs_stream` — TTFT / total latency  
4. `04_tool_calling` — tool call + bounded multi-turn loop  
5. `05_reasoning_mode` — `no_think` / `low` / `high`  
6. `06_error_handling_retry` — timeout / 429 / network + backoff  

Shared helpers: [`common.py`](./common.py)  
Quickstart: [`../quickstart.md`](../quickstart.md) · [`../quickstart_CN.md`](../quickstart_CN.md)

## Setup

```bash
pip install -r examples/requirements.txt
cp examples/.env.example examples/.env   # optional; do not commit .env
```

| Variable | Default | Notes |
|:---|:---|:---|
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | TokenHub: `https://tokenhub.tencentmaas.com/v1` |
| `HY3_API_KEY` | `EMPTY` | TokenHub: your key (env only) |
| `HY3_MODEL` | `hy3` | served model name |
| `HY3_TIMEOUT` | `120` | seconds |

## Run

```bash
python examples/en/01_basic_chat.py
# or
python examples/cn/01_basic_chat.py
```

## Tests & lint

```bash
pip install -r examples/requirements-dev.txt

# Format + lint (ruff)
ruff format --check examples
ruff check examples

# Offline unit tests (no API key):
pytest examples/tests -q -k "not live"

# Optional live smoke (TokenHub or local):
# HY3_LIVE=1 HY3_BASE_URL=... HY3_API_KEY=... pytest examples/tests/test_live_smoke.py -q
```

**Never commit API keys.** Rotate any key that was pasted into chat, issues, or screenshots.
