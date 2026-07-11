import argparse
import json
import os
import random
import time
from collections.abc import Callable
from typing import Any

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)


base_url = os.getenv(
    "HY3_BASE_URL",
    "http://127.0.0.1:8000/v1",
)

api_key = os.getenv(
    "HY3_API_KEY",
    "EMPTY",
)

model = os.getenv(
    "HY3_MODEL",
    "hy3",
)


# Disable SDK-level retries so this example can
# demonstrate the manual retry loop explicitly.
client = OpenAI(
    base_url=base_url,
    api_key=api_key,
    max_retries=0,
)


MAX_ATTEMPTS = 4
BASE_DELAY_SECONDS = 1.0
MAX_DELAY_SECONDS = 8.0


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


RETRYABLE_ERRORS = (
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    InternalServerError,
)


def print_request() -> None:
    """Print the complete request payload."""

    print("=== Complete request ===")

    print(
        json.dumps(
            REQUEST_PAYLOAD,
            indent=2,
            ensure_ascii=False,
        )
    )


def error_name(error: Exception) -> str:
    """Return a readable category for a retryable error."""

    if isinstance(error, RateLimitError):
        return "rate limit"

    if isinstance(error, APITimeoutError):
        return "timeout"

    if isinstance(error, APIConnectionError):
        return "connection"

    if isinstance(error, InternalServerError):
        return "server"

    return type(error).__name__


def get_retry_after(
    error: Exception,
) -> float | None:
    """Read a numeric Retry-After header when available."""

    if not isinstance(error, APIStatusError):
        return None

    value = error.response.headers.get(
        "retry-after"
    )

    if value is None:
        return None

    try:
        delay = float(value)
    except ValueError:
        return None

    if delay <= 0:
        return None

    return delay


def calculate_backoff_delay(
    attempt: int,
) -> float:
    """Calculate exponential backoff with jitter."""

    exponential_delay = min(
        BASE_DELAY_SECONDS * (2 ** (attempt - 1)),
        MAX_DELAY_SECONDS,
    )

    jitter_multiplier = random.uniform(
        0.75,
        1.25,
    )

    return exponential_delay * jitter_multiplier


def choose_retry_delay(
    error: Exception,
    attempt: int,
) -> tuple[float, str]:
    """Prefer Retry-After, otherwise use backoff with jitter."""

    retry_after = get_retry_after(error)

    if retry_after is not None:
        return retry_after, "Retry-After header"

    return (
        calculate_backoff_delay(attempt),
        "exponential backoff with jitter",
    )


def call_with_retry(
    operation: Callable[[], Any],
) -> Any:
    """Run an operation with bounded retries."""

    for attempt in range(
        1,
        MAX_ATTEMPTS + 1,
    ):
        try:
            print(
                f"\nAttempt "
                f"{attempt}/{MAX_ATTEMPTS}"
            )

            result = operation()

            print("Request succeeded.")
            return result

        except RETRYABLE_ERRORS as error:
            category = error_name(error)

            print(
                f"Caught retryable "
                f"{category} error:"
            )
            print(error)

            if attempt == MAX_ATTEMPTS:
                print(
                    "Maximum attempts reached. "
                    "Giving up."
                )
                raise

            delay, source = choose_retry_delay(
                error,
                attempt,
            )

            print(
                f"Retrying in {delay:.2f}s "
                f"using {source}."
            )

            time.sleep(delay)

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
            print(error)

            raise

    raise RuntimeError(
        "Retry loop ended unexpectedly."
    )


def live_request() -> Any:
    """Send a real Hy3 API request."""

    return client.chat.completions.create(
        **REQUEST_PAYLOAD
    )


def make_http_request() -> httpx.Request:
    """Create a request object for simulated SDK errors."""

    return httpx.Request(
        "POST",
        f"{base_url.rstrip('/')}/chat/completions",
    )


def make_simulated_error(
    error_type: str,
) -> Exception:
    """Create an OpenAI SDK error for deterministic demos."""

    request = make_http_request()

    if error_type == "timeout":
        return APITimeoutError(
            request
        )

    if error_type == "connection":
        return APIConnectionError(
            request=request,
        )

    if error_type == "rate_limit":
        response = httpx.Response(
            status_code=429,
            headers={
                "retry-after": "1"
            },
            request=request,
        )

        return RateLimitError(
            "Simulated rate limit error.",
            response=response,
            body={
                "error": {
                    "type": "rate_limit_error",
                    "code": "429001",
                }
            },
        )

    if error_type == "server":
        response = httpx.Response(
            status_code=503,
            request=request,
        )

        return InternalServerError(
            "Simulated service unavailable error.",
            response=response,
            body={
                "error": {
                    "type": "server_error",
                    "code": "503001",
                }
            },
        )

    raise ValueError(
        f"Unsupported simulation type: {error_type}"
    )


def make_simulated_operation(
    error_type: str,
    failures_before_success: int = 2,
) -> Callable[[], dict[str, Any]]:
    """Return an operation that fails predictably before success."""

    call_count = 0

    def operation() -> dict[str, Any]:
        nonlocal call_count

        call_count += 1

        if call_count <= failures_before_success:
            raise make_simulated_error(
                error_type
            )

        return {
            "status": "success",
            "attempt": call_count,
            "message": (
                "Simulated request succeeded "
                "after retries."
            ),
        }

    return operation


def print_result(
    result: Any,
) -> None:
    """Parse either a live or simulated successful result."""

    print("\n=== Parsed successful result ===")

    if isinstance(result, dict):
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    print(
        "Finish reason:",
        result.choices[0].finish_reason,
    )

    print(
        "Content:",
        result.choices[0].message.content,
    )

    if result.usage is not None:
        print(
            "Prompt tokens:",
            result.usage.prompt_tokens,
        )
        print(
            "Completion tokens:",
            result.usage.completion_tokens,
        )
        print(
            "Total tokens:",
            result.usage.total_tokens,
        )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Hy3 error handling and retry example."
        )
    )

    parser.add_argument(
        "--simulate",
        choices=[
            "none",
            "timeout",
            "rate_limit",
            "connection",
            "server",
        ],
        default="none",
        help=(
            "Simulate retryable failures. "
            "Use 'none' for a real API request."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Run either a real request or a deterministic retry demo."""

    args = parse_args()

    print_request()

    if args.simulate == "none":
        print("\nMode: live API request")

        operation = live_request

    else:
        print(
            f"\nMode: simulated "
            f"{args.simulate} errors"
        )

        operation = make_simulated_operation(
            args.simulate
        )

    result = call_with_retry(
        operation
    )

    print_result(
        result
    )


if __name__ == "__main__":
    main()
