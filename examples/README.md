<p align="left">
   English ｜ <a href="README_cn.md">中文</a>
</p>

# Hy3 API examples

This directory contains runnable Python examples for both the TokenHub Chat Completions API and Responses API. Python files use English names and comments; Chinese and English explanations are provided as separate Markdown files.

## Prerequisites

Set the API key in the repository root `.env` file or in the current shell:

```bash
export HY3_API_KEY="YOUR_TOKENHUB_API_KEY"
export HY3_BASE_URL="https://tokenhub.tencentmaas.com/v1"
```

Install dependencies and run an example from the repository root:

```bash
uv sync
uv run --env-file .env python examples/01_basic_chat.py
```

Do not write real API keys into Python files or commit `.env`.

## Examples

| File                                                                     | Description                               | Chinese guide                                                                  |
|--------------------------------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------------------|
| [`01_basic_chat.py`](01_basic_chat.py)                                   | Minimal Chat Completions request.         | [`01_basic_chat_cn.md`](01_basic_chat_cn.md)                                   |
| [`02_streaming.py`](02_streaming.py)                                     | Chat Completions streaming and usage.     | [`02_streaming_cn.md`](02_streaming_cn.md)                                     |
| [`03_streaming_vs_non_streaming.py`](03_streaming_vs_non_streaming.py)   | Compare streaming latency and total time. | [`03_streaming_vs_non_streaming_cn.md`](03_streaming_vs_non_streaming_cn.md)   |
| [`04_tool_calling.py`](04_tool_calling.py)                               | Chat Completions function tool loop.      | [`04_tool_calling_cn.md`](04_tool_calling_cn.md)                               |
| [`05_reasoning_mode.py`](05_reasoning_mode.py)                           | Compare normal and reasoning modes.       | [`05_reasoning_mode_cn.md`](05_reasoning_mode_cn.md)                           |
| [`06_responses_basic.py`](06_responses_basic.py)                         | Minimal Responses API request.            | [`06_responses_basic_cn.md`](06_responses_basic_cn.md)                         |
| [`07_responses_streaming.py`](07_responses_streaming.py)                 | Parse Responses SSE events.               | [`07_responses_streaming_cn.md`](07_responses_streaming_cn.md)                 |
| [`08_responses_tool_calling.py`](08_responses_tool_calling.py)           | Responses function-call output loop.      | [`08_responses_tool_calling_cn.md`](08_responses_tool_calling_cn.md)           |
| [`09_responses_structured_output.py`](09_responses_structured_output.py) | JSON Schema output and parsing.           | [`09_responses_structured_output_cn.md`](09_responses_structured_output_cn.md) |
| [`10_error_handling_retry.py`](10_error_handling_retry.py)               | Retry transient errors with backoff.      | [`10_error_handling_retry_cn.md`](10_error_handling_retry_cn.md)               |

Every Python example has a matching English Markdown guide and a Chinese Markdown guide. Output can vary with model versions, sampling, service load, and network latency.

The weather function is fixed demo data and does not call a real weather service.

`07_responses_streaming.py` parses SSE with the Python standard library. The current TokenHub `response.created` event may contain `output: null`, which can cause high-level Responses stream parsers in some OpenAI SDK versions to fail.

Parameter and protocol support should be verified against the [Hy3 calling guide](https://cloud.tencent.com/document/product/1823/132252) and the [TokenHub language-model overview](https://cloud.tencent.com/document/product/1823/130079).
