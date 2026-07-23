# Hy3 API examples

These examples accompany the repository-level [API quickstart](../../quickstart.md).
They use the OpenAI-compatible endpoint documented by Hy3 and share only a small,
tested transport helper. Every numbered script remains directly runnable from
the repository root.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r examples/api/requirements.txt
cp examples/api/.env.example examples/api/.env
```

Edit `.env` for the endpoint you actually operate. It is ignored by Git.

## Index

| # | Walkthrough | Script |
| --- | --- | --- |
| 01 | [Basic chat](./01_basic_chat.md) | [`01_basic_chat.py`](./01_basic_chat.py) |
| 02 | [Streaming](./02_streaming.md) | [`02_streaming.py`](./02_streaming.py) |
| 03 | [Latency comparison](./03_latency_comparison.md) | [`03_latency_comparison.py`](./03_latency_comparison.py) |
| 04 | [Tool calling](./04_tool_calling.md) | [`04_tool_calling.py`](./04_tool_calling.py) |
| 05 | [Reasoning modes](./05_reasoning_modes.md) | [`05_reasoning_modes.py`](./05_reasoning_modes.py) |
| 06 | [Error handling and retry](./06_error_handling_retry.md) | [`06_error_handling_retry.py`](./06_error_handling_retry.py) |

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `HY3_BASE_URL` | `http://127.0.0.1:8000/v1` | OpenAI-compatible root URL |
| `HY3_API_KEY` | `EMPTY` | Non-empty local placeholder or hosted API key |
| `HY3_MODEL` | `hy3` | Served model name |
| `HY3_TIMEOUT` | `120` | Request timeout in seconds |
| `HY3_BENCH_RUNS` | `3` | Runs per mode in example 03 |
| `HY3_SHOW_REASONING` | `0` | Print reasoning text in example 05 only when set to `1` |

The helper disables OpenAI SDK retries. Example 06 therefore demonstrates all
retry behavior explicitly rather than stacking two retry policies.

## Offline verification

```bash
python -m pip install -r examples/api/requirements-dev.txt
ruff format --check --config examples/api/ruff.toml examples/api
ruff check --config examples/api/ruff.toml examples/api
pytest -q examples/api/tests
```

Offline checks validate parsing, retry policy, file contracts, and syntax. They
do not prove that an endpoint or model works; run every script against Hy3 before
publishing live-result claims.
