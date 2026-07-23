"""Hy3 API example 06: bounded retries for transient API failures."""

from __future__ import annotations

from hy3_client import Hy3Config, call_with_retry, create_client, reasoning_options
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError


def main() -> None:
    config = Hy3Config.from_env()
    client = create_client(config)
    print(f"Connecting with {config.safe_summary()}")

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
            extra_body=reasoning_options("no_think"),
        )

    def report_retry(attempt: int, delay: float, error: BaseException) -> None:
        print(f"Attempt {attempt} failed with {type(error).__name__}; retrying in {delay:.2f}s")

    try:
        response = call_with_retry(request, attempts=4, on_retry=report_retry)
    except AuthenticationError:
        raise SystemExit(
            "Authentication failed: check HY3_API_KEY (this error is not retried)."
        ) from None
    except APITimeoutError:
        raise SystemExit(
            "The request timed out after all attempts; increase HY3_TIMEOUT if needed."
        ) from None
    except APIConnectionError:
        raise SystemExit("Could not reach HY3_BASE_URL after all attempts.") from None
    except APIStatusError as error:
        raise SystemExit(f"API returned HTTP {error.status_code}: {error.message}") from error

    print("Assistant: " + (response.choices[0].message.content or ""))


if __name__ == "__main__":
    main()
