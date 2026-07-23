# 06 — Error handling and bounded retry

Retries help with transient failures but make permanent failures slower and can
duplicate side effects. This example disables OpenAI SDK retries, then applies
one visible, testable policy around a read-only chat request.

## Run

```bash
python examples/api/06_error_handling_retry.py
```

## Complete request

```python
def request():
    return client.chat.completions.create(
        model=config.model,
        messages=[
            {
                "role": "user",
                "content": "Return one short sentence explaining exponential backoff.",
            }
        ],
        temperature=0.0,
        max_tokens=128,
        extra_body={
            "chat_template_kwargs": {"reasoning_effort": "no_think"}
        },
    )

response = call_with_retry(request, attempts=4, on_retry=report_retry)
```

`create_client` uses `max_retries=0`. Without that setting, SDK retries and
example retries would stack and make the real number of requests hard to see.

## Retry classification

The helper retries:

- connection errors;
- request timeouts;
- rate-limit responses;
- HTTP 408, 409, 429, 500, 502, 503, and 504.

It does not retry authentication, malformed requests, missing models, or other
client errors. Exponential backoff uses full jitter and a maximum delay:

```python
cap = min(max_delay, base_delay * (2 ** (attempt - 1)))
delay = cap * random.random()
delay = max(delay, retry_after_from_response or 0.0)
time.sleep(delay)
```

Both numeric and HTTP-date `Retry-After` values are supported.

## Complete response and error handling

```python
try:
    response = call_with_retry(request, attempts=4, on_retry=report_retry)
except AuthenticationError:
    raise SystemExit("Authentication failed: check HY3_API_KEY.")
except APITimeoutError:
    raise SystemExit("The request timed out after all attempts.")
except APIConnectionError:
    raise SystemExit("Could not reach HY3_BASE_URL after all attempts.")
except APIStatusError as error:
    raise SystemExit(f"API returned HTTP {error.status_code}: {error.message}")

print(response.choices[0].message.content or "")
```

## Example output

Success after a transient failure, illustrative format:

```text
Attempt 1 failed with RateLimitError; retrying in <seconds>s
Assistant: Exponential backoff increases the wait between repeated attempts.
```

Permanent failure, illustrative format:

```text
Authentication failed: check HY3_API_KEY (this error is not retried).
```

## Production checks

- Cap attempts and individual request timeouts.
- Honor `Retry-After` and reduce concurrency when rate limited.
- Retry non-idempotent tool actions only with an idempotency strategy.
- Log error class, status, attempt, and delay—never authorization headers.
- Add circuit breaking or a queue when sustained overload is expected.
