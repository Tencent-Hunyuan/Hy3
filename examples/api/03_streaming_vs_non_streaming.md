# 03 Streaming versus non-streaming

[简体中文](03_streaming_vs_non_streaming_CN.md) · [Index](README.md) · [Script](03_streaming_vs_non_streaming.py)

## Purpose

Show which latency each API style can expose. [`03_streaming_vs_non_streaming.py`](03_streaming_vs_non_streaming.py) measures non-streaming total time, streaming first output, streaming first visible content, and streaming total time.

## Configuration

Configure a backend through `examples/api/.env`. Use `--warmup` when you want one unmeasured request before the comparison. Both measured modes use the same question, model, temperature, top-p, token limit, and reasoning mapping.

## Complete request

The shared base request is:

```python
request = {
    "model": config.model,
    "messages": [
        {
            "role": "user",
            "content": "Explain idempotency in APIs in three sentences.",
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
    "max_tokens": 256,
    "extra_body": reasoning_extra_body(config, "no_think"),
}
```

The non-streaming call sends that dictionary unchanged. The streaming call creates a new dictionary with exactly two additions:

```python
stream_request = {
    **request,
    "stream": True,
    "stream_options": {"include_usage": True},
}
```

When enabled, warmup sends the unchanged base request once before either measurement.

## Response parsing

- `measure_non_streaming` records one interval around the SDK call.
- `measure_streaming` records `started`, then iterates chunks through `StreamAccumulator`.
- **First output** is the first non-empty reasoning or content update.
- **First visible content** is the first non-empty content update. Reasoning may arrive earlier and is not printed as user-visible content.
- **Total** is recorded after stream iteration finishes.

The function returns timing dataclasses only. It does not retain or compare answer text, so this example measures timing mechanics rather than response quality.

## Run

From the repository root:

```bash
python examples/api/03_streaming_vs_non_streaming.py
python examples/api/03_streaming_vs_non_streaming.py --warmup
```

These commands use the configured API and live clock. The first block is one live observation without warmup; the second uses injected test clocks.

## Example output

**Verified live evidence summary (sanitized; not literal stdout)**

The script's actual CLI output uses fixed English timing labels. This list is a reviewed summary of one observation, not a transcript or benchmark:

- Backend: OpenRouter
- Model requested: `tencent/hy3:free`
- Response model: unavailable in this script's retained result
- Observed on: 2026-07-11
- Non-streaming total: 4.465s
- Streaming first output: 1.306s
- Streaming first content: 1.306s
- Streaming total: 3.175s

These numbers are one transient observation, not a benchmark or a claim that streaming is always faster.

**Deterministic offline example**

```text
Non-streaming total: 0.750s
Streaming first output: 0.100s
Streaming first content: 0.400s
Streaming total: 1.000s
```

The non-streaming and streaming numbers come from deterministic unit-test clocks. They are fixtures for parsing and formatting, not a live benchmark and not evidence that one mode is faster.

## Limitations

- Do not generalize from either the single live observation or the fixture values as if they were a benchmark.
- A fair live comparison needs repeated trials, controlled load, the same backend, and the same prompt/sampling settings.
- `first_output_seconds` and `first_content_seconds` are `None` when no reasoning/content delta appears; the CLI prints `unavailable`.
- The example does not validate semantic equivalence between the two answers.
- Optional warmup changes server/client state and must be reported when publishing measurements.
