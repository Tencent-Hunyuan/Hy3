# 05 Reasoning mode

[简体中文](05_reasoning_mode_CN.md) · [Index](README.md) · [Script](05_reasoning_mode.py)

## Purpose

Compare `no_think` and `high` while holding the question and standard request fields constant. [`05_reasoning_mode.py`](05_reasoning_mode.py) records normalized reasoning, content, usage, and elapsed time for each mode.

## Configuration

Configure either backend in `examples/api/.env`. The comparison function accepts only `no_think` and `high`; passing `low` raises `ValueError` before reading the clock or calling the SDK.

Mapping differs by backend:

| Comparison mode | Self-hosted SDK `extra_body` | OpenRouter SDK `extra_body` |
|---|---|---|
| `no_think` | `{"chat_template_kwargs": {"reasoning_effort": "no_think"}}` | `{"reasoning": {"effort": "none"}}` |
| `high` | `{"chat_template_kwargs": {"reasoning_effort": "high"}}` | `{"reasoning": {"effort": "high"}}` |

## Complete request

Both calls use the exact same question and standard fields:

```python
QUESTION = "A train travels 120 km in 2 hours. What is its average speed?"

client.chat.completions.create(
    model=config.model,
    messages=[{"role": "user", "content": QUESTION}],
    temperature=0.9,
    top_p=1.0,
    max_tokens=512,
    extra_body=reasoning_extra_body(config, effort),
)
```

`main` uses one client and calls `run_mode` in this order:

```python
for effort in ("no_think", "high"):
    result = run_mode(client, config, effort, QUESTION)
```

## Response parsing

`summarize_completion` normalizes content, reasoning text, structured reasoning details, finish reason, and usage. `ModeResult` retains:

- the requested effort;
- normalized reasoning and details;
- content, converted to an empty string when absent;
- elapsed seconds from the injected/default clock;
- usage as a plain dict or `None`.

Missing reasoning is valid. `main` prints an availability note only when both reasoning text and reasoning details are empty. The response can still contain valid assistant content.

## Run

From the repository root:

```bash
python examples/api/05_reasoning_mode.py
```

The command uses the configured backend. The next block uses deterministic fake completions and injected clocks.

## Example output

**Deterministic offline example**

```text
no_think:
  content: 60 km/h
  reasoning: ""
  reasoning_details: []
  elapsed: 0.100s
  usage.total_tokens: 7

high:
  content: 60 km/h
  reasoning: distance divided by time
  reasoning_details: []
  elapsed: 0.300s
  usage.total_tokens: 7
```

The times above come from injected unit-test clocks. They are not live latency measurements.

## Limitations

- The fixture does not prove that one mode is faster or more accurate.
- Reasoning fields are optional and backend dependent; absent reasoning is not an error.
- The comparison covers only `no_think` and `high`, not `low`.
- Do not expose model reasoning without reviewing provider behavior and your product's policy.
- `frozen=True` prevents replacing dataclass fields but nested list/dict values remain ordinary Python containers.
