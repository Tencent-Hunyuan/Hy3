# Example 6: Error Handling & Retry

Production-grade error handling for the Hy3 API — handle timeouts, rate limits, network errors, and server errors with automatic retry and exponential backoff.

## What You'll Learn

- Identify and classify common API errors
- Implement retry with exponential backoff
- Handle rate limiting gracefully
- Set timeouts and handle network errors
- Build a production-ready API wrapper

---

## Common Error Types

| Error | HTTP Code | Typical Cause | Retryable? |
|:---|:---|:---|:---|
| `BadRequestError` | 400 | Invalid parameters, bad tool schema | ❌ No |
| `AuthenticationError` | 401 | Wrong API key | ❌ No |
| `RateLimitError` | 429 | Too many requests | ✅ Yes |
| `InternalServerError` | 500 | Server-side error | ✅ Yes |
| `APITimeoutError` | — | Request timed out | ✅ Yes |
| `APIConnectionError` | — | Network issue | ✅ Yes |
| `APIError` | other | Other API errors | ⚠️ Maybe |

---

## Basic Error Handling

```python
from openai import (
    OpenAI,
    BadRequestError,
    AuthenticationError,
    RateLimitError,
    InternalServerError,
    APITimeoutError,
    APIConnectionError,
    APIError,
)

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
    timeout=60.0,  # 60-second timeout
)

def safe_chat(messages, **kwargs):
    """Make a chat completion request with basic error handling."""
    try:
        response = client.chat.completions.create(
            model="hy3",
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content

    except BadRequestError as e:
        print(f"❌ Bad request (400): {e}")
        print("   Check your parameters, tool schema, or message format.")
        raise

    except AuthenticationError as e:
        print(f"❌ Authentication failed (401): {e}")
        print("   Check your API key.")
        raise

    except RateLimitError as e:
        print(f"⏳ Rate limited (429): {e}")
        print("   Slow down your requests or increase your quota.")
        raise

    except APITimeoutError as e:
        print(f"⏰ Request timed out: {e}")
        print("   Try increasing timeout or reducing max_tokens.")
        raise

    except APIConnectionError as e:
        print(f"🔌 Connection error: {e}")
        print("   Check if the server is running and reachable.")
        raise

    except InternalServerError as e:
        print(f"💥 Server error (500): {e}")
        print("   The server encountered an error. Retry may help.")
        raise

    except APIError as e:
        print(f"⚠️  API error ({e.status_code}): {e}")
        raise

    except Exception as e:
        print(f"🔥 Unexpected error: {type(e).__name__}: {e}")
        raise
```

---

## Retry with Exponential Backoff

The most reliable approach: retry on transient errors with increasing delays.

```python
import time
import random

RETRYABLE_ERRORS = (
    RateLimitError,
    InternalServerError,
    APITimeoutError,
    APIConnectionError,
)


def chat_with_retry(
    messages,
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    **kwargs,
):
    """
    Make a chat completion request with automatic retry + exponential backoff.

    Args:
        messages: List of message dicts.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds (doubles each retry).
        max_delay: Maximum delay cap in seconds.

    Returns:
        The assistant's reply text.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                **kwargs,
            )
            return response.choices[0].message.content

        except RETRYABLE_ERRORS as e:
            last_error = e

            if attempt == max_retries:
                print(f"❌ All {max_retries} retries exhausted. Last error: {e}")
                raise

            # Exponential backoff with jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.5)
            wait = delay + jitter

            print(f"🔄 Retry {attempt + 1}/{max_retries} after {wait:.1f}s "
                  f"({type(e).__name__})")

            time.sleep(wait)

        except (BadRequestError, AuthenticationError) as e:
            # Non-retryable — fail immediately
            print(f"❌ Non-retryable error: {type(e).__name__}: {e}")
            raise

    raise last_error
```

### Retry Timeline

```
Attempt 0: fails with 429 RateLimitError
  → wait ~1.2s (base 1s + jitter)

Attempt 1: fails with 500 InternalServerError
  → wait ~2.3s (base 2s + jitter)

Attempt 2: fails with APITimeoutError
  → wait ~4.6s (base 4s + jitter)

Attempt 3: succeeds ✅
```

---

## Handling Rate Limits (429)

When the server returns 429 (Too Many Requests), check for `Retry-After` header:

```python
def chat_with_rate_limit_handling(messages, **kwargs):
    """Handle rate limiting with Retry-After header support."""
    while True:
        try:
            response = client.chat.completions.create(
                model="hy3",
                messages=messages,
                **kwargs,
            )
            return response.choices[0].message.content

        except RateLimitError as e:
            # Check for Retry-After header
            retry_after = getattr(e, "response", None)
            if retry_after is not None:
                retry_after = retry_after.headers.get("Retry-After")
            retry_after = retry_after if retry_after else None

            if retry_after:
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = 5.0
                print(f"⏳ Rate limited. Waiting {wait:.0f}s (per Retry-After header)...")
            else:
                wait = 5.0
                print(f"⏳ Rate limited. Waiting {wait:.0f}s...")

            time.sleep(wait)

        except APITimeoutError:
            print("⏰ Timeout — retrying with shorter max_tokens...")
            kwargs["max_tokens"] = max(64, kwargs.get("max_tokens", 256) // 2)
```

---

## Timeout Configuration

```python
# Global timeout (applies to all requests)
client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
    timeout=120.0,  # 120 seconds
)

# Per-request timeout override
response = client.chat.completions.create(
    model="hy3",
    messages=[{"role": "user", "content": "..."}],
    timeout=30.0,  # 30 seconds for this specific request
)

# Separate connect vs. read timeout
from httpx import Timeout

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="EMPTY",
    timeout=Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0),
)
```

---

## Full Production Wrapper

Combining everything into a reusable class:

```python
class Hy3Client:
    """Production-grade Hy3 API client with retry, timeout, and error handling."""

    def __init__(
        self,
        base_url="http://127.0.0.1:8000/v1",
        api_key="EMPTY",
        timeout=120.0,
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
    ):
        self.client = OpenAI(base_url=base_url, api_key=api_key, timeout=timeout)
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def chat(self, messages, **kwargs):
        """Send a chat request with automatic retry on transient errors."""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model="hy3",
                    messages=messages,
                    **kwargs,
                )
                return response

            except (RateLimitError, InternalServerError,
                    APITimeoutError, APIConnectionError) as e:
                last_error = e
                if attempt == self.max_retries:
                    raise

                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                jitter = random.uniform(0, delay * 0.5)
                time.sleep(delay + jitter)

            except (BadRequestError, AuthenticationError) as e:
                raise  # Non-retryable

        raise last_error

    def chat_content(self, messages, **kwargs):
        """Convenience: return content string directly."""
        return self.chat(messages, **kwargs).choices[0].message.content
```

### Usage

```python
hy3 = Hy3Client(max_retries=3, timeout=60.0)

# Safe, retryable chat
try:
    reply = hy3.chat_content([
        {"role": "user", "content": "Explain quantum computing."},
    ])
    print(reply)
except BadRequestError:
    print("Invalid request — check your parameters.")
except Exception as e:
    print(f"Failed after all retries: {e}")
```

---

## Key Takeaways

1. **Always set a timeout** — `timeout=120.0` prevents hanging requests.
2. **Retry transient errors** — 429, 500, timeouts, and connection errors are retryable.
3. **Use exponential backoff with jitter** — prevents thundering herd on recovery.
4. **Never retry 400 (Bad Request)** — fix the request instead.
5. **Check `Retry-After` headers** for rate limits to avoid wasting retries.
6. **Cap max_delay** at 60s to avoid excessive waits.
7. **Log every retry** — it helps with debugging and monitoring.

---

## Run the Script

```bash
pip install openai
python 06-error-handling.py
```
