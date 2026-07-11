# 06 Error handling and retry

[简体中文](06_error_handling_retry_CN.md) · [Index](README.md) · [Script](06_error_handling_retry.py)

## Purpose

Add a visible, bounded application retry policy around an OpenAI-compatible request. [`06_error_handling_retry.py`](06_error_handling_retry.py) also provides a deterministic `--simulate` mode that needs no API configuration or network.

## Configuration

For a live call, configure `examples/api/.env`. The script creates the SDK client with `max_retries=0`, so only the application policy controls retries. Defaults are four total attempts, `base_delay=0.5`, and `max_delay=8.0` for exponential jitter.

Simulation deliberately bypasses environment loading and client creation.

## Complete request

The live client and complete request are:

```python
client = create_client(config, max_retries=0)

client.chat.completions.create(
    model=config.model,
    messages=[
        {
            "role": "user",
            "content": "Give one sentence about reliable API clients.",
        }
    ],
    temperature=0.9,
    top_p=1.0,
    max_tokens=128,
    extra_body=reasoning_extra_body(config, "no_think"),
)
```

That operation is passed to:

```python
call_with_retry(operation, on_retry=print_retry)
```

The default policy retries SDK connection/timeouts and responses with status 408, 409, 429, or 5xx. Other statuses are re-raised immediately.

## Response parsing

On each caught `Exception`, `call_with_retry`:

1. Checks whether the error is retryable and whether attempts remain.
2. Reads a non-negative, finite numeric `Retry-After` value when available.
3. Otherwise computes `min(max_delay, base_delay * 2 ** (attempt - 1))` and multiplies it by `random.random()` for full jitter.
4. Calls `on_retry(next_attempt, max_attempts, delay, error)`, then sleeps.
5. Re-raises the final failure without another callback or sleep.

`summarize_completion` parses a successful response into content, optional reasoning/details, finish reason, and usage. Callback or sleep exceptions are not swallowed. `KeyboardInterrupt` and other `BaseException` values are outside the retry catch.

## Run

Deterministic offline simulation:

```bash
python examples/api/06_error_handling_retry.py --simulate
```

Live configured request:

```bash
python examples/api/06_error_handling_retry.py
```

## Example output

**Verified live observation**

```text
Backend: OpenRouter
Model requested: tencent/hy3:free
Model resolved: tencent/hy3-20260706:free
Observed on: 2026-07-11

Retry 2/4 in 0.00s after APIConnectionError
Retry 3/4 in 0.25s after APIConnectionError
Retry 4/4 in 1.73s after APIConnectionError
content: one sentence about reliable API clients
usage.total_tokens: 49
```

This is one transient live recovery observation. The exact failure sequence and jitter delays are not promised to recur.

**Deterministic offline simulation**

```text
Retry 2/4 in 0.00s after RateLimitError
rate_limit: recovered
Retry 2/4 in 0.00s after APITimeoutError
timeout: recovered
Retry 2/4 in 0.00s after APIConnectionError
connection: recovered
```

The deterministic simulation injects one error per scenario, disables actual sleeping, uses deterministic jitter, and then returns `recovered`.

## Limitations

- Only finite numeric Retry-After seconds are parsed; HTTP-date values fall back to jitter.
- The live connection-error sequence above is observational evidence, not fixed script output.
- A Retry-After value is not capped by `max_delay`; decide whether your production policy needs an additional upper bound.
- The default random source is suitable for jitter, not cryptography.
- The policy is synchronous and sleeps the current thread.
- Retrying a non-idempotent operation can repeat side effects. The example request is illustrative; assess each operation before retrying it.
- The example does not add circuit breaking, shared retry budgets, observability, or thread coordination.
- The live CLI relies on process exit to release the client.
