"""06 error handling: timeout / rate limit / network retry with backoff."""
import os
import random
import time
from typing import Any, Callable

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

client = OpenAI(
    api_key=os.environ.get("HY3_API_KEY", "EMPTY"),
    base_url=os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1"),
    timeout=30.0,
)
MODEL = os.environ.get("HY3_MODEL", "hy3")


def with_retry(
    fn: Callable[[], Any],
    *,
    max_retries: int = 4,
    base_delay: float = 0.8,
) -> Any:
    """Retry on timeout / rate limit / connection errors with exponential backoff."""
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            last_err = e
            kind = type(e).__name__
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "rate limit" in msg or "timeout" in msg:
                last_err = e
                kind = "retryable"
            else:
                raise
        if attempt >= max_retries:
            break
        delay = base_delay * (2**attempt) + random.uniform(0, 0.25)
        print(f"[retry] attempt={attempt + 1} kind={kind} sleep={delay:.2f}s err={last_err!r}")
        time.sleep(delay)
    raise RuntimeError(f"failed after retries: {last_err}")


def normal_call():
    print("=== normal call with retry wrapper ===")
    resp = with_retry(
        lambda: client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "只回答：OK"}],
            max_tokens=16,
            temperature=0,
        )
    )
    print("ok:", resp.choices[0].message.content)


def demo_backoff_policy():
    print("\n=== backoff policy (demo, no real failure required) ===")
    print("On RateLimitError / APITimeoutError / APIConnectionError:")
    for attempt in range(4):
        delay = 0.8 * (2**attempt)
        print(f"  attempt {attempt + 1} -> sleep ~{delay:.1f}s then retry")
    print("After max_retries exhausted -> raise RuntimeError")


def demo_flaky_logic():
    print("\n=== flaky function + retry (local simulation) ===")
    state = {"n": 0}

    def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise TimeoutError(f"simulated timeout #{state['n']}")
        return "success-after-retries"

    def with_retry_generic(fn, max_retries=5, base_delay=0.15):
        last = None
        for attempt in range(max_retries + 1):
            try:
                return fn()
            except TimeoutError as e:
                last = e
                if attempt >= max_retries:
                    break
                delay = base_delay * (2**attempt)
                print(f"[retry] {e}; sleep {delay:.2f}s")
                time.sleep(delay)
        raise RuntimeError(last)

    print("result:", with_retry_generic(flaky))


if __name__ == "__main__":
    normal_call()
    demo_backoff_policy()
    demo_flaky_logic()
