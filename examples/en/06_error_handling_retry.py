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
