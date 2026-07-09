# 06 Error Handling & Retry

## Introduction

This example demonstrates error handling and **exponential-backoff retry** when calling Hy3 (OpenAI-compatible API), covering three typical scenarios:

1. **Timeout (`APITimeoutError`)**: forced with a very short `timeout`; retries are exhausted and then it fails gracefully.
2. **Rate limit (`RateLimitError`, HTTP 429)**: shows how to identify a 429 and back off according to a rate-limit policy.
3. **Network error (`APIConnectionError`)**: forced with a wrong `base_url`; retries and then fails gracefully.

Retry logic uses the `tenacity` library with exponential backoff against transient errors (timeout / rate limit / network error), up to 5 attempts. Each scenario is wrapped in `try/except`, and **the script runs safely standalone** — even without an Hy3 service, scenarios 1 and 3 trigger errors as expected.

---

## Prerequisites

1. Install dependencies:
   ```bash
   pip install tenacity openai
   ```

2. Configure connection info via environment variables (defaults suit a local deployment):
   ```bash
   set HY3_BASE_URL=http://127.0.0.1:8000/v1
   set HY3_API_KEY=EMPTY
   ```

3. To demonstrate the "normal call" path (the non-rate-limited branch of scenario 2), start the Hy3 service first (vLLM / SGLang). Scenarios 1 and 3 can trigger errors without any service.

---

## Complete Request

```python
"""
Hy3 Error Handling & Retry Example
==================================

Demonstrates common error handling and exponential-backoff retry when calling Hy3
(OpenAI-compatible API), covering three scenarios:
  1. Timeout (APITimeoutError): forced with a very short timeout; retry; on persistent failure, handle gracefully.
  2. Rate limit (RateLimitError, HTTP 429): shows how to catch and back off on 429.
  3. Network error (APIConnectionError): forced with a wrong base_url; retry; fail gracefully.

Retry logic uses the tenacity library with exponential backoff against
APITimeoutError / RateLimitError / APIConnectionError (up to 5 attempts).
Every scenario is wrapped in try/except so the script runs safely standalone
(even without an Hy3 service, the error scenarios trigger as expected).

Dependencies: pip install tenacity openai

Connection info is configured via environment variables (with defaults):
  HY3_BASE_URL  default http://127.0.0.1:8000/v1
  HY3_API_KEY   default EMPTY
"""

import os

from openai import (
    OpenAI,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    APIStatusError,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

MODEL = "hy3"

# Initialize the client via environment variables (with defaults) for easy deployment switching
client = OpenAI(
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
)


# ---------------------------------------------------------------------------
# 1. Define a call wrapper with exponential-backoff retry
# ---------------------------------------------------------------------------
# Retry policy:
#   - Only retry APITimeoutError / RateLimitError / APIConnectionError
#     (these are typically transient errors where retrying makes sense)
#   - wait_exponential: exponential backoff, wait time = min(max, multiplier * 2^(attempt-1))
#                       here multiplier=1, min=1, max=10
#                       i.e. 1s, 2s, 4s, 8s, 10s (capped by max) ...
#   - stop_after_attempt(5): retry at most 5 times
#   - APIStatusError (other HTTP errors, e.g. 400/500) is NOT retried; it is raised directly
@retry(
    retry=retry_if_exception_type(
        (APITimeoutError, RateLimitError, APIConnectionError)
    ),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(5),
    reraise=True,
)
def chat_with_retry(messages, **kwargs):
    """Chat completion call with exponential-backoff retry."""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        top_p=1.0,
        extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        **kwargs,
    )


def header(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# ---------------------------------------------------------------------------
# 2. Scenario 1: Timeout (APITimeoutError)
# ---------------------------------------------------------------------------
def scenario_timeout():
    header("Scenario 1: Timeout (APITimeoutError)")
    print("Note: a very short timeout=0.001s is set, which almost certainly times out.")
    print("Expected: tenacity triggers exponential-backoff retry; after retries are exhausted, APITimeoutError is raised and caught by try/except.\n")

    # Use a separate client to force a very short timeout (without affecting the global client)
    short_timeout_client = OpenAI(
        base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
        api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
        timeout=0.001,
    )

    @retry(
        retry=retry_if_exception_type(
            (APITimeoutError, RateLimitError, APIConnectionError)
        ),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def call():
        return short_timeout_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.9,
            top_p=1.0,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )

    try:
        call()
        print("[Result] Call succeeded (timeout not triggered).")
    except APITimeoutError as e:
        print(f"[Caught APITimeoutError] Timeout retries exhausted.")
        print(f"  Error type: {type(e).__name__}")
        print(f"  Suggestion: increase timeout appropriately, or reduce the request/context size and retry.")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# 3. Scenario 2: Rate limit (RateLimitError, HTTP 429)
# ---------------------------------------------------------------------------
def scenario_rate_limit():
    header("Scenario 2: Rate limit (RateLimitError, HTTP 429)")
    print("Note: simulates how to identify and back off when the server returns 429.")
    print("Expected: RateLimitError is caught by retry and retried with exponential backoff; here we construct it manually to show the identification logic.\n")

    # When a real 429 is returned by the server, the OpenAI SDK raises RateLimitError automatically.
    # Here we use try/except to demonstrate how to identify and handle this exception type.
    try:
        # Attempt a normal call; if the server actually rate-limits, it raises RateLimitError
        # (this is mainly to show the catch-and-handle logic)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.9,
            top_p=1.0,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )
        print("[Result] Call succeeded; rate limit not triggered.")
        print(f"  Returned content: {response.choices[0].message.content[:50]} ...")
    except RateLimitError as e:
        print(f"[Caught RateLimitError] Server returned 429; rate limit triggered.")
        print(f"  Error type: {type(e).__name__}")
        # HTTP 429 is the typical status code for rate limiting
        status = getattr(getattr(e, "response", None), "status_code", None)
        print(f"  HTTP status code: {status}")
        print(f"  Suggestion: lower concurrency/request frequency, retry after exponential backoff; contact ops to raise the quota if needed.")
    except APIStatusError as e:
        # Other HTTP errors (non-429) go here
        print(f"[Caught APIStatusError] Non-429 HTTP error.")
        print(f"  Error type: {type(e).__name__}")
        print(f"  HTTP status code: {getattr(e, 'status_code', 'unknown')}")
        print(f"  Suggestion: troubleshoot by status code (4xx -> check request, 5xx -> check server).")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# 4. Scenario 3: Network error (APIConnectionError)
# ---------------------------------------------------------------------------
def scenario_network_error():
    header("Scenario 3: Network error (APIConnectionError)")
    print("Note: uses an unreachable base_url to force a connection error.")
    print("Expected: tenacity retries with exponential backoff; after retries are exhausted, APIConnectionError is raised and caught by try/except.\n")

    # Build a client with an address that is definitely unreachable
    bad_client = OpenAI(
        base_url="http://127.0.0.1:9/v1",  # almost no service listens on port 9
        api_key="EMPTY",
    )

    @retry(
        retry=retry_if_exception_type(
            (APITimeoutError, RateLimitError, APIConnectionError)
        ),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def call():
        return bad_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好"}],
            temperature=0.9,
            top_p=1.0,
            extra_body={"chat_template_kwargs": {"reasoning_effort": "no_think"}},
        )

    try:
        call()
        print("[Result] Call succeeded (network error not triggered).")
    except APIConnectionError as e:
        print(f"[Caught APIConnectionError] Network connection failed; retries exhausted.")
        print(f"  Error type: {type(e).__name__}")
        cause = getattr(e, "__cause__", None) or e
        print(f"  Root cause: {cause}")
        print(f"  Suggestion: check whether base_url is correct, whether the Hy3 service is running, and whether the network/firewall allows the port.")
    except Exception as e:
        print(f"[Caught other exception] {type(e).__name__}: {e}")


def main():
    print("Hy3 Error Handling & Retry Example")
    print("This script runs standalone; even without an Hy3 service, scenarios 1 and 3 trigger errors as expected.")

    scenario_timeout()
    scenario_rate_limit()
    scenario_network_error()

    header("All scenarios demonstrated")
    print("Key takeaways:")
    print("  - APITimeoutError    -> increase timeout or reduce request size; retryable")
    print("  - RateLimitError(429)-> lower concurrency/frequency, retry after exponential backoff")
    print("  - APIConnectionError-> check base_url / service status / network")
    print("  - APIStatusError     -> handle by HTTP status code (4xx -> request, 5xx -> server)")


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

> The following is sample output (not a real run result) to illustrate the print layout and error messages of each scenario. The actual root-cause text varies by environment.

```text
Hy3 Error Handling & Retry Example
This script runs standalone; even without an Hy3 service, scenarios 1 and 3 trigger errors as expected.

======================================================================
Scenario 1: Timeout (APITimeoutError)
======================================================================
Note: a very short timeout=0.001s is set, which almost certainly times out.
Expected: tenacity triggers exponential-backoff retry; after retries are exhausted, APITimeoutError is raised and caught by try/except.

[Caught APITimeoutError] Timeout retries exhausted.
  Error type: APITimeoutError
  Suggestion: increase timeout appropriately, or reduce the request/context size and retry.

======================================================================
Scenario 2: Rate limit (RateLimitError, HTTP 429)
======================================================================
Note: simulates how to identify and back off when the server returns 429.
Expected: RateLimitError is caught by retry and retried with exponential backoff; here we construct it manually to show the identification logic.

[Caught RateLimitError] Server returned 429; rate limit triggered.
  Error type: RateLimitError
  HTTP status code: 429
  Suggestion: lower concurrency/request frequency, retry after exponential backoff; contact ops to raise the quota if needed.

======================================================================
Scenario 3: Network error (APIConnectionError)
======================================================================
Note: uses an unreachable base_url to force a connection error.
Expected: tenacity retries with exponential backoff; after retries are exhausted, APIConnectionError is raised and caught by try/except.

[Caught APIConnectionError] Network connection failed; retries exhausted.
  Error type: APIConnectionError
  Root cause: Connection error.
  Suggestion: check whether base_url is correct, whether the Hy3 service is running, and whether the network/firewall allows the port.

======================================================================
All scenarios demonstrated
======================================================================
Key takeaways:
  - APITimeoutError    -> increase timeout or reduce request size; retryable
  - RateLimitError(429)-> lower concurrency/frequency, retry after exponential backoff
  - APIConnectionError-> check base_url / service status / network
  - APIStatusError     -> handle by HTTP status code (4xx -> request, 5xx -> server)
```
