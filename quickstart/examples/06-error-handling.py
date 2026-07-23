"""
Example 6: Error Handling & Retry — production-grade error handling for Hy3 API.

Covers:
    - Error type identification and classification
    - Retry with exponential backoff + jitter
    - Rate limit handling with Retry-After header
    - Timeout configuration
    - Production-ready client wrapper

Usage:
    python 06-error-handling.py

Prerequisites:
    - Hy3 server running at http://127.0.0.1:8000 (vLLM or SGLang)
    - pip install openai
"""

import time
import random
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

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
BASE_URL = "http://127.0.0.1:8000/v1"
API_KEY = "EMPTY"
MODEL = "hy3"

RETRYABLE_ERRORS = (
    RateLimitError,
    InternalServerError,
    APITimeoutError,
    APIConnectionError,
)

NON_RETRYABLE_ERRORS = (
    BadRequestError,
    AuthenticationError,
)

client = OpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=120.0)


# ──────────────────────────────────────────────────────────────────────
# 1. Basic Error Classification
# ──────────────────────────────────────────────────────────────────────
def demonstrate_error_types():
    """Show how to catch and classify different OpenAI API errors."""
    print("=" * 60)
    print("1. ERROR TYPE CLASSIFICATION")
    print("=" * 60)

    test_cases = [
        # (description, kwargs, expected_error)
        ("Valid request", {
            "messages": [{"role": "user", "content": "Hello!"}],
            "max_tokens": 32,
        }, None),
        ("Invalid model name", {
            "model": "nonexistent-model",
            "messages": [{"role": "user", "content": "Hello!"}],
        }, "error"),
        ("Missing messages (should 400)", {
            # messages intentionally omitted — this will raise a TypeError
            # from the SDK before hitting the API, so we handle it separately
        }, "TypeError"),
    ]

    # Test 1: Normal request — should succeed
    print("\n--- Test: Valid request ---")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say 'hello' in one word."}],
            temperature=0.9,
            top_p=1.0,
            max_tokens=16,
        )
        print(f"✅ Success: {response.choices[0].message.content}")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

    # Test 2: Bad model name — should get 400
    print("\n--- Test: Invalid model name ---")
    try:
        response = client.chat.completions.create(
            model="nonexistent-model",
            messages=[{"role": "user", "content": "Hello!"}],
        )
        print(f"✅ Success (unexpected): {response.choices[0].message.content}")
    except BadRequestError as e:
        print(f"❌ BadRequestError (400) — as expected: {e}")
        print("   → This is NOT retryable. Fix the model name.")
    except Exception as e:
        print(f"❌ Other error: {type(e).__name__}: {e}")


# ──────────────────────────────────────────────────────────────────────
# 2. Retry with Exponential Backoff
# ──────────────────────────────────────────────────────────────────────
def chat_with_retry(
    messages,
    max_retries=3,
    base_delay=1.0,
    max_delay=60.0,
    **kwargs,
):
    """
    Chat completion with automatic retry + exponential backoff + jitter.

    Retryable errors: RateLimitError, InternalServerError,
                      APITimeoutError, APIConnectionError
    Non-retryable:    BadRequestError, AuthenticationError

    Args:
        messages: List of message dicts.
        max_retries: Max retry attempts (default: 3).
        base_delay: Initial delay in seconds, doubles each retry.
        max_delay: Maximum delay cap in seconds.

    Returns:
        The full ChatCompletion response object.
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                **kwargs,
            )
            if attempt > 0:
                print(f"   ✅ Succeeded on attempt {attempt + 1}")
            return response

        except RETRYABLE_ERRORS as e:
            last_error = e

            if attempt == max_retries:
                print(f"   ❌ All {max_retries} retries exhausted.")
                raise

            # Exponential backoff: 1s → 2s → 4s → ... capped at max_delay
            delay = min(base_delay * (2 ** attempt), max_delay)
            # Add jitter: ±25% random variation to avoid thundering herd
            jitter = random.uniform(-delay * 0.25, delay * 0.25)
            wait = max(0.1, delay + jitter)

            print(f"   🔄 Retry {attempt + 1}/{max_retries} after {wait:.1f}s "
                  f"({type(e).__name__}: {str(e)[:80]})")

            time.sleep(wait)

        except NON_RETRYABLE_ERRORS as e:
            print(f"   ❌ Non-retryable error: {type(e).__name__}: {e}")
            raise

    raise last_error


def demonstrate_retry_logic():
    """Show how the retry wrapper works with a normal request."""
    print("\n" + "=" * 60)
    print("2. RETRY WITH EXPONENTIAL BACKOFF")
    print("=" * 60)
    print("   (Making a normal request — retries only trigger on errors)\n")

    try:
        response = chat_with_retry(
            messages=[{"role": "user", "content": "What is 2+2? Answer in one word."}],
            max_retries=3,
            temperature=0.9,
            top_p=1.0,
            max_tokens=32,
        )
        print(f"\n   📝 Response: {response.choices[0].message.content}")
        print(f"   🔢 Tokens:   {response.usage.total_tokens}")
    except Exception as e:
        print(f"\n   ❌ Failed: {type(e).__name__}: {e}")


# ──────────────────────────────────────────────────────────────────────
# 3. Rate Limit Handling with Retry-After
# ──────────────────────────────────────────────────────────────────────
def chat_with_rate_limit_handling(messages, **kwargs):
    """
    Handle rate limits with Retry-After header support.

    When the server returns 429, it may include a Retry-After header
    indicating how long to wait. This function respects that header.
    """
    while True:
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                **kwargs,
            )
            return response

        except RateLimitError as e:
            # Try to extract Retry-After header
            retry_after = None
            try:
                if hasattr(e, "response") and e.response:
                    retry_after = e.response.headers.get("Retry-After")
            except Exception:
                pass

            if retry_after:
                try:
                    wait = float(retry_after)
                except ValueError:
                    wait = 5.0
                print(f"   ⏳ Rate limited. Respecting Retry-After: {wait:.0f}s")
            else:
                wait = 5.0
                print(f"   ⏳ Rate limited. No Retry-After header. Waiting {wait:.0f}s...")

            time.sleep(wait)

        except RETRYABLE_ERRORS as e:
            print(f"   🔄 Transient error: {type(e).__name__}. Retrying in 2s...")
            time.sleep(2)


# ──────────────────────────────────────────────────────────────────────
# 4. Timeout Configuration
# ──────────────────────────────────────────────────────────────────────
def demonstrate_timeouts():
    """Show different timeout configurations."""
    print("\n" + "=" * 60)
    print("3. TIMEOUT CONFIGURATION")
    print("=" * 60)

    # Per-request timeout
    print("\n--- Per-request timeout (30s) ---")
    try:
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Say hello."}],
            max_tokens=16,
            timeout=30.0,
        )
        elapsed = time.perf_counter() - start
        print(f"   ✅ Completed in {elapsed:.2f}s")
        print(f"   📝 {response.choices[0].message.content}")
    except APITimeoutError:
        print("   ⏰ Request timed out after 30s")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {e}")

    # Short timeout that may trigger (for demonstration)
    print("\n--- Aggressive timeout (0.001s) — will likely fire ---")
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Write a very long essay about the history of Rome."}],
            max_tokens=2048,
            timeout=0.001,  # Impossible timeout — will fire immediately
        )
        print(f"   ✅ Unexpected success")
    except APITimeoutError:
        print("   ⏰ APITimeoutError caught — this is expected with 0.001s timeout")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {e}")


# ──────────────────────────────────────────────────────────────────────
# 5. Production-Grade Client Wrapper
# ──────────────────────────────────────────────────────────────────────
class Hy3Client:
    """
    Production-grade Hy3 API client with built-in retry, timeout,
    and comprehensive error handling.

    Usage:
        hy3 = Hy3Client(max_retries=3)
        reply = hy3.chat_content([{"role": "user", "content": "Hello"}])
    """

    def __init__(
        self,
        base_url=BASE_URL,
        api_key=API_KEY,
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
        """Send a chat request with retry. Returns full ChatCompletion object."""
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    **kwargs,
                )
                return response

            except RETRYABLE_ERRORS as e:
                last_error = e
                if attempt == self.max_retries:
                    raise

                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                jitter = random.uniform(-delay * 0.25, delay * 0.25)
                wait = max(0.1, delay + jitter)

                print(f"   🔄 [{type(e).__name__}] Retry {attempt + 1}/{self.max_retries} "
                      f"in {wait:.1f}s")

                time.sleep(wait)

            except NON_RETRYABLE_ERRORS as e:
                raise

        raise last_error

    def chat_content(self, messages, **kwargs):
        """Convenience method: return content string directly."""
        return self.chat(messages, **kwargs).choices[0].message.content

    def chat_stream(self, messages, **kwargs):
        """Stream a chat response, yielding content deltas."""
        kwargs["stream"] = True
        response = self.chat(messages, **kwargs)
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def demonstrate_client_wrapper():
    """Show the production client wrapper in action."""
    print("\n" + "=" * 60)
    print("4. PRODUCTION CLIENT WRAPPER")
    print("=" * 60)

    hy3 = Hy3Client(max_retries=3, timeout=60.0)

    # Normal chat
    print("\n--- Normal chat ---")
    try:
        reply = hy3.chat_content(
            [{"role": "user", "content": "Explain APIs in one sentence."}],
            temperature=0.9,
            max_tokens=128,
        )
        print(f"   📝 {reply}")
    except Exception as e:
        print(f"   ❌ {type(e).__name__}: {e}")

    # Streaming via wrapper
    print("\n--- Streaming via wrapper ---")
    try:
        for token in hy3.chat_stream(
            [{"role": "user", "content": "Count from 1 to 5."}],
            temperature=0.9,
            max_tokens=64,
        ):
            print(token, end="", flush=True)
        print()
    except Exception as e:
        print(f"\n   ❌ {type(e).__name__}: {e}")


# ──────────────────────────────────────────────────────────────────────
# 6. Error Recovery Strategy Summary
# ──────────────────────────────────────────────────────────────────────
def print_strategy_summary():
    print("\n" + "=" * 60)
    print("5. RECOVERY STRATEGY SUMMARY")
    print("=" * 60)

    print("""
    ┌──────────────────────┬──────────┬──────────────────────────────┐
    │ Error                │ Retry?   │ Strategy                     │
    ├──────────────────────┼──────────┼──────────────────────────────┤
    │ BadRequestError(400) │ NO       │ Fix parameters, tool schema  │
    │ AuthError(401)       │ NO       │ Check API key                │
    │ RateLimitError(429)  │ YES      │ Retry-After + backoff        │
    │ InternalError(500)   │ YES      │ Exponential backoff + jitter │
    │ APITimeoutError      │ YES      │ Increase timeout, backoff    │
    │ APIConnectionError   │ YES      │ Check server, backoff        │
    │ Other APIError       │ MAYBE    │ Depends on status code       │
    └──────────────────────┴──────────┴──────────────────────────────┘

    Backoff formula: delay = min(base_delay * 2^attempt, max_delay)
    Jitter: ±25% random variation to avoid thundering herd
    Non-retryable: fail immediately, surface error to caller
    """)


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    demonstrate_error_types()
    demonstrate_retry_logic()
    demonstrate_timeouts()
    demonstrate_client_wrapper()
    print_strategy_summary()
