# Error Handling and Retry

This example demonstrates robust error handling and bounded retry behavior for the Hy3 OpenAI-compatible API.

It covers:

* API timeouts
* rate limits
* network and connection errors
* server-side 5xx errors
* exponential backoff
* random jitter
* `Retry-After` handling
* maximum retry limits
* deterministic error simulation

The example supports both real API requests and controlled failure simulations.

## Prerequisites

Before running this example, make sure you have:

* Python 3.10 or later
* the `openai` Python package installed
* the `httpx` package installed
* access to a Hy3 OpenAI-compatible endpoint for live requests

The example reads:

```text
HY3_BASE_URL
HY3_API_KEY
HY3_MODEL
```

If these variables are not set, it uses:

```text
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
```

## Run a live API request

From the repository root:

```bash
python examples/api/06_error_handling_retry.py
```

In live mode, the script sends a real Hy3 API request through the retry wrapper.

## Run simulated failures

The example can simulate retryable failures without intentionally overloading an API or breaking the local network.

### Simulate a timeout

```bash
python examples/api/06_error_handling_retry.py --simulate timeout
```

### Simulate rate limiting

```bash
python examples/api/06_error_handling_retry.py --simulate rate_limit
```

### Simulate a connection failure

```bash
python examples/api/06_error_handling_retry.py --simulate connection
```

### Simulate a server error

```bash
python examples/api/06_error_handling_retry.py --simulate server
```

Each simulation fails twice and succeeds on the third attempt.

This makes retry behavior deterministic and easy to inspect.

## Complete request

The live request payload is:

```python
REQUEST_PAYLOAD = {
    "model": model,
    "messages": [
        {
            "role": "user",
            "content": (
                "Explain exponential backoff "
                "in two short sentences."
            ),
        }
    ],
    "temperature": 0.9,
    "top_p": 1.0,
}
```

The live API operation is:

```python
def live_request() -> Any:
    return client.chat.completions.create(
        **REQUEST_PAYLOAD
    )
```

## Disabling SDK-level retries

The client is created with:

```python
client = OpenAI(
    base_url=base_url,
    api_key=api_key,
    max_retries=0,
)
```

This example disables SDK-level retries because it explicitly demonstrates its own retry loop.

Without this setting, SDK retries and application retries could overlap, making the number and timing of actual requests harder to understand.

In production applications, decide carefully whether to:

* rely on SDK retry behavior
* implement application-level retries
* combine both with clearly defined limits

Avoid uncontrolled nested retry loops.

## Retryable errors

The example retries:

```python
RETRYABLE_ERRORS = (
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)
```

These categories represent:

```text
RateLimitError
→ request rate exceeded

APITimeoutError
→ request timed out

APIConnectionError
→ network or connection failure

InternalServerError
→ server-side 5xx failure
```

## Bounded retry loop

The example limits the total number of attempts:

```python
MAX_ATTEMPTS = 4
```

The retry loop is:

```python
for attempt in range(
    1,
    MAX_ATTEMPTS + 1,
):
    try:
        result = operation()
        return result

    except RETRYABLE_ERRORS as error:
        ...
```

The first request counts as attempt 1.

With:

```text
MAX_ATTEMPTS = 4
```

the operation can run at most four times.

When the final attempt also fails:

```python
if attempt == MAX_ATTEMPTS:
    print(
        "Maximum attempts reached. "
        "Giving up."
    )
    raise
```

The original exception is re-raised.

## Exponential backoff

When the server does not provide an explicit retry delay, the example calculates:

```python
BASE_DELAY_SECONDS * (2 ** (attempt - 1))
```

With:

```python
BASE_DELAY_SECONDS = 1.0
```

the nominal delays are:

```text
Attempt 1 failure → 1 second
Attempt 2 failure → 2 seconds
Attempt 3 failure → 4 seconds
Attempt 4 failure → 8 seconds
```

The delay is capped:

```python
MAX_DELAY_SECONDS = 8.0
```

Implementation:

```python
exponential_delay = min(
    BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
    MAX_DELAY_SECONDS,
)
```

## Jitter

The example adds random jitter:

```python
jitter_multiplier = random.uniform(
    0.75,
    1.25,
)
```

The final delay is:

```python
return exponential_delay * jitter_multiplier
```

For example, a nominal delay of:

```text
2.00 seconds
```

might become:

```text
1.83 seconds
2.11 seconds
2.28 seconds
```

Jitter helps reduce synchronized retries when many clients fail at the same time.

Without jitter:

```text
many clients fail
    ↓
all wait exactly 2 seconds
    ↓
all retry together
    ↓
server receives another traffic spike
```

With jitter:

```text
client A → retry after 1.8s
client B → retry after 2.1s
client C → retry after 2.3s
```

Retry traffic is spread over time.

## Retry-After handling

Some HTTP responses explicitly tell clients how long to wait before retrying.

The example reads:

```python
value = error.response.headers.get(
    "retry-after"
)
```

When a valid numeric value exists, it is preferred over locally calculated backoff:

```python
if retry_after is not None:
    return retry_after, "Retry-After header"
```

Otherwise, the client falls back to:

```text
exponential backoff with jitter
```

## Rate-limit example

The deterministic rate-limit simulation creates an HTTP 429 response with:

```python
headers={
    "retry-after": "1"
}
```

The observed output was:

```text
Mode: simulated rate_limit errors

Attempt 1/4
Caught retryable rate limit error:
Simulated rate limit error.
Retrying in 1.00s using Retry-After header.

Attempt 2/4
Caught retryable rate limit error:
Simulated rate limit error.
Retrying in 1.00s using Retry-After header.

Attempt 3/4
Request succeeded.

=== Parsed successful result ===
{
  "status": "success",
  "attempt": 3,
  "message": "Simulated request succeeded after retries."
}
```

This demonstrates that the client prefers the explicit server-provided delay.

## Connection-error example

The deterministic connection simulation does not provide a `Retry-After` value.

The observed output was:

```text
Mode: simulated connection errors

Attempt 1/4
Caught retryable connection error:
Connection error.
Retrying in 0.91s using exponential backoff with jitter.

Attempt 2/4
Caught retryable connection error:
Connection error.
Retrying in 2.28s using exponential backoff with jitter.

Attempt 3/4
Request succeeded.

=== Parsed successful result ===
{
  "status": "success",
  "attempt": 3,
  "message": "Simulated request succeeded after retries."
}
```

The exact delays vary between runs because jitter is random.

In this run:

```text
First retry delay:  0.91s
Second retry delay: 2.28s
```

The underlying nominal exponential delays were approximately:

```text
1s
2s
```

before jitter was applied.

## Timeout simulation

A timeout can be simulated with:

```bash
python examples/api/06_error_handling_retry.py --simulate timeout
```

The example creates:

```python
APITimeoutError(
    request
)
```

Because no `Retry-After` header exists, the retry loop uses exponential backoff with jitter.

## Server-error simulation

A service failure can be simulated with:

```bash
python examples/api/06_error_handling_retry.py --simulate server
```

The example creates a simulated HTTP 503 response and wraps it as:

```python
InternalServerError(
    "Simulated service unavailable error.",
    response=response,
    body={
        "error": {
            "type": "server_error",
            "code": "503001",
        }
    },
)
```

This allows server retry behavior to be tested without requiring a real service outage.

## Non-retryable API status errors

Not every API error should be retried.

The example handles other API status errors separately:

```python
except APIStatusError as error:
    print(
        "Caught non-retryable API "
        "status error."
    )
    print(
        f"Status code: "
        f"{error.status_code}"
    )
    print(
        f"Request ID: "
        f"{error.request_id}"
    )
    raise
```

For example, repeatedly retrying a malformed request may not help.

Applications should distinguish between:

```text
transient failures
→ retry may succeed

permanent request errors
→ retrying the same request may fail again
```

## Response parsing

For a live successful request, the example parses:

```python
result.choices[0].finish_reason
```

and:

```python
result.choices[0].message.content
```

When usage information is available, it also prints:

```python
result.usage.prompt_tokens
result.usage.completion_tokens
result.usage.total_tokens
```

For a simulated successful result, the example prints the returned dictionary as JSON.

## Production considerations

This example is intentionally small and educational.

Production retry policies should consider:

* idempotency
* request deadlines
* maximum total retry time
* queueing behavior
* service-specific rate limits
* provider-specific error codes
* observability and logging
* cancellation
* circuit breakers
* concurrency limits

Retries are not always safe.

For operations with side effects, repeated execution can create duplicate actions unless the API provides idempotency guarantees.

## What this example demonstrates

This example shows:

1. how to catch retryable SDK exceptions
2. how to bound the total number of attempts
3. how to calculate exponential backoff
4. how to add jitter
5. how to prefer `Retry-After`
6. how to distinguish retryable and non-retryable failures
7. how to avoid overlapping SDK and application retry loops
8. how to test retry behavior with deterministic simulations
9. how to parse successful live and simulated results
