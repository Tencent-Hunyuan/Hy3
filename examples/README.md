<p align="left">
    <a href="./zh-cn/README.md">中文</a>&nbsp;｜&nbsp;English
</p>
<br>

# Hy3 API Examples

These examples show common Hy3 OpenAI-compatible API patterns. Start with the [API Quickstart](../quickstart.md) if you have not configured the client environment yet.

## Setup

Install the client dependency from the repository root:

```bash
python -m pip install -r requirements.txt
```

Set the server connection variables:

```bash
export HY3_BASE_URL="${HY3_BASE_URL:-http://127.0.0.1:8000/v1}"
export HY3_API_KEY="${HY3_API_KEY:-EMPTY}"
export HY3_MODEL="${HY3_MODEL:-hy3}"
```

## Example Index

| Guide | Script | What it demonstrates |
| --- | --- | --- |
| [01. Basic chat](01_basic_chat.md) | [`01_basic_chat.py`](01_basic_chat.py) | Single-turn and multi-turn chat. |
| [02. Streaming](02_streaming.md) | [`02_streaming.py`](02_streaming.py) | Streaming request and chunk-by-chunk parsing. |
| [03. Latency compare](03_latency_compare.md) | [`03_latency_compare.py`](03_latency_compare.py) | Non-streaming total latency vs streaming first-token and total latency. |
| [04. Tool calling](04_tool_calling.md) | [`04_tool_calling.py`](04_tool_calling.py) | One tool-call response and a multi-turn application-side tool loop. |
| [05. Reasoning mode](05_reasoning_mode.md) | [`05_reasoning_mode.py`](05_reasoning_mode.py) | `no_think` vs `high` reasoning mode behavior. |
| [06. Error handling & retry](06_error_handling_retry.md) | [`06_error_handling_retry.py`](06_error_handling_retry.py) | Timeout, rate limit, network error, and retryable server error handling. |

Run any script from the repository root, for example:

```bash
python examples/01_basic_chat.py
```
