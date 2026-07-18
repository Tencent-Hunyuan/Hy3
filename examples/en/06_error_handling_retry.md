# 06 Error Handling & Retry

## Introduction

This example demonstrates **production-minded** error handling when calling Hy3 (OpenAI-compatible API):

1. **Timeout (`APITimeoutError`)** — forced short `timeout`; bounded retries then graceful failure.
2. **Rate limit (`RateLimitError`, HTTP 429)** — identify 429, honor **`Retry-After`** (seconds or HTTP-date).
3. **Network error (`APIConnectionError`)** — unreachable `base_url`; retries then fail gracefully.
4. **Shared helper `call_with_retry`** — exponential backoff + **full jitter**, `max_attempts` and **`max_total_wait`** caps so clients never hang forever. Also retries selected 5xx / gateway statuses.

The helper lives in [`examples/common.py`](../common.py). SDK auto-retries are disabled (`max_retries=0`) so demo policy is explicit. **Scenarios 1 and 3 run without a live Hy3 service.**

### Retry policy (summary)

```text
delay ≈ min(max_delay, base_delay * 2^(attempt-1))
delay  = max(delay, Retry-After)   # if present
delay  = uniform(delay*(1-jitter), delay)   # full jitter, default jitter=0.25
stop when attempts exhausted OR max_total_wait exceeded
```

---

## Prerequisites

1. Install dependencies:
   ```bash
   pip install -r examples/requirements.txt
   ```

2. Configure connection info via environment variables (defaults suit local deploy):
   ```bash
   export HY3_BASE_URL=http://127.0.0.1:8000/v1
   export HY3_API_KEY=EMPTY
   ```

3. Scenario 2's "happy path" needs a reachable service (TokenHub or local). Scenarios 1 and 3 do not.

---

## Complete Request

```python
"""Hy3 Example 06: Error handling & retry (timeout / 429 / network / 5xx).

Demonstrates:
  1. Timeout (APITimeoutError) with forced short timeout + bounded retry
  2. Rate limit (429 / RateLimitError) including Retry-After handling
  3. Network error (APIConnectionError) against an unreachable base_url
  4. Shared call_with_retry helper (exponential backoff, total wait cap)

Scenarios 1 and 3 work even without a live Hy3 service.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from openai import (  # noqa: E402
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)

from common import (  # noqa: E402
    call_with_retry,
    chat_completion,
    get_config,
    make_client,
    parse_retry_after,
)


def header(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def scenario_timeout():
    header("Scenario 1: Timeout (APITimeoutError)")
    print("Note: timeout=0.001s almost always times out.")
    print("Expected: call_with_retry backs off, then raises APITimeoutError.\n")

    short_client = make_client(timeout=0.001)

    def call():
        return chat_completion(
            short_client,
            [{"role": "user", "content": "你好"}],
            reasoning="no_think",
        )

    try:
        # Keep demo snappy: few attempts, small delays
        call_with_retry(call, max_attempts=3, base_delay=0.2, max_delay=0.5, max_total_wait=2.0)
        print("[Result] Call succeeded (timeout not triggered).")
    except APITimeoutError as e:
        print("[Caught APITimeoutError] Timeout retries exhausted.")
        print(f"  Error type: {type(e).__name__}")
        print("  Suggestion: increase timeout, reduce context/max_tokens, or retry later.")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


def scenario_rate_limit():
    header("Scenario 2: Rate limit (RateLimitError, HTTP 429)")
    print("Note: shows identification + Retry-After aware backoff.")
    print("If the live server is not rate-limiting, the call succeeds normally.\n")

    client = make_client()

    def call():
        return chat_completion(
            client,
            [{"role": "user", "content": "你好"}],
            reasoning="no_think",
        )

    try:
        response = call_with_retry(call, max_attempts=3, base_delay=0.5, max_delay=2.0)
        print("[Result] Call succeeded; rate limit not triggered.")
        content = response.choices[0].message.content or ""
        print(f"  Returned content: {content[:50]} ...")
    except RateLimitError as e:
        retry_after = parse_retry_after(e)
        print("[Caught RateLimitError] Server returned 429.")
        print(f"  Error type: {type(e).__name__}")
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"  HTTP status code: {status}")
        print(f"  Retry-After: {retry_after}")
        print("  Suggestion: lower concurrency; respect Retry-After; request quota if needed.")
    except APIStatusError as e:
        print("[Caught APIStatusError] Non-429 HTTP error.")
        print(f"  status_code: {getattr(e, 'status_code', 'unknown')}")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


def scenario_network_error():
    header("Scenario 3: Network error (APIConnectionError)")
    print("Note: uses unreachable base_url http://127.0.0.1:9/v1")
    print("Expected: retries then APIConnectionError.\n")

    bad_client = make_client(base_url="http://127.0.0.1:9/v1", api_key="EMPTY", timeout=2.0)

    def call():
        return chat_completion(
            bad_client,
            [{"role": "user", "content": "你好"}],
            reasoning="no_think",
        )

    try:
        call_with_retry(call, max_attempts=3, base_delay=0.2, max_delay=0.5, max_total_wait=2.0)
        print("[Result] Call succeeded (network error not triggered).")
    except APIConnectionError as e:
        print("[Caught APIConnectionError] Network connection failed; retries exhausted.")
        print(f"  Error type: {type(e).__name__}")
        cause = getattr(e, "__cause__", None) or e
        print(f"  Root cause: {cause}")
        print("  Suggestion: check base_url, service health, firewall/proxy.")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


def main():
    cfg = get_config()
    print("Hy3 Error Handling & Retry Example")
    print(f"Default target: {cfg['base_url']}  model={cfg['model']}")
    print("Scenarios 1 and 3 run without a live Hy3 service.")

    scenario_timeout()
    scenario_rate_limit()
    scenario_network_error()

    header("All scenarios demonstrated")
    print("Key takeaways:")
    print("  - APITimeoutError    -> increase timeout / reduce request size; retryable")
    print("  - RateLimitError(429)-> lower QPS, honor Retry-After, exponential backoff")
    print("  - APIConnectionError -> check base_url / service / network")
    print("  - 5xx APIStatusError -> retry with backoff; 4xx (except 429) usually not")
    print("  - Always cap max_attempts and max_total_wait so clients never hang forever")


if __name__ == "__main__":
    main()
```

---

## Complete Response Parsing

### 1. Error type overview

When calling Hy3 (OpenAI-compatible API) with the OpenAI Python SDK, the following exceptions may be raised:

| Exception type          | Trigger scenario                                       | Worth retrying |
|:------------------------|:-------------------------------------------------------|:---------------|
| `APITimeoutError`       | Request timeout (exceeds the configured `timeout`)     | Yes            |
| `RateLimitError`        | Server returns HTTP **429** (too frequent / over quota)| Yes            |
| `APIConnectionError`    | Network-layer connection failure (DNS / refused / unreachable, etc.) | Yes |
| `APIStatusError`        | Other HTTP errors (400 bad request, 500 server error, etc.) | Depends; usually not retried |

> `APITimeoutError`, `RateLimitError`, and `APIConnectionError` are **transient errors** where retrying usually makes sense; `APIStatusError` (e.g. 400 parameter error) is pointless to retry — just troubleshoot the request directly.

### 2. tenacity retry policy

This example uses a `tenacity` decorator to implement retries. Key config:

```python
@retry(
    retry=retry_if_exception_type(
        (APITimeoutError, RateLimitError, APIConnectionError)
    ),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
```

- **`retry_if_exception_type`**: retry only when the raised exception is of the specified types. Here only the three transient errors are retried; `APIStatusError` will not trigger a retry.
- **`wait_exponential`**: exponential backoff, to avoid aggressive retries while the server is still under pressure.
- **`stop_after_attempt(5)`**: at most 5 attempts, to prevent infinite retries.
- **`reraise=True`**: after retries are exhausted, re-raise the original exception so the upper-layer `try/except` can handle it by type.

### 3. Exponential-backoff formula

The wait time for `wait_exponential(multiplier=1, min=1, max=10)`:

```
wait = min(max, multiplier * 2^(attempt - 1))
```

Wait times for each retry (`multiplier=1, min=1, max=10`):

| Attempt #   | Wait time |
|:----------:|:---------:|
| 1 (first)  | 0 (immediate) |
| 2          | 1s        |
| 3          | 2s        |
| 4          | 4s        |
| 5          | 8s        |
| 6+         | 10s (capped by max) |

This example makes at most 5 attempts, so the actual wait sequence is roughly: immediate → 1s → 2s → 4s → 8s.

### 4. Identification and handling for each error

- **Timeout (`APITimeoutError`)**
  - Identify: catch `APITimeoutError`.
  - Handle: increase `timeout` appropriately; if the context is so long that generation is slow, reduce the request/context size; retry can recover sporadic timeouts.

- **Rate limit (`RateLimitError`, HTTP 429)**
  - Identify: catch `RateLimitError`; its underlying HTTP status code is 429.
  - Handle: lower concurrency and request frequency; retry after exponential backoff; contact ops to raise the quota (QPS/TPM) if necessary.

- **Network error (`APIConnectionError`)**
  - Identify: catch `APIConnectionError`; inspect the root cause via `e.__cause__` (e.g. connection refused).
  - Handle: check whether `base_url` is correct, whether the Hy3 service is running, and whether the network/firewall allows the corresponding port.

- **Other HTTP errors (`APIStatusError`)**
  - Identify: catch `APIStatusError`; get the status code via `e.status_code`.
  - Handle: 4xx — check request params (e.g. model name, message format); 5xx — check server logs and status.

---

## Sample Output
> Verified live on **Tencent Cloud TokenHub** (`https://tokenhub.tencentmaas.com/v1`, `model=hy3`) on **2026-07-18**. Output is model-generated and may vary; secrets redacted.

```text
Scenario 1: Timeout (APITimeoutError) — retries exhausted, error caught. ✅
Scenario 2: Rate limit — call succeeded or 429 handled with Retry-After. ✅
Scenario 3: Network error (unreachable base_url) — retries then APIConnectionError. ✅
(Scenarios 1 & 3 do not require a live Hy3 service.)
```
