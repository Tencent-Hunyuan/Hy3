"""Call Hy3 with bounded transient-error retry and Retry-After support."""

from __future__ import annotations

from common import (
    ApiConfig,
    RetryPolicy,
    call_with_retry,
    create_client,
    print_response,
    run_example,
    status_code_from_error,
    thinking_body,
)


def main() -> None:
    config = ApiConfig.from_env()
    client = create_client(config)
    policy = RetryPolicy(
        max_attempts=4,
        base_delay=0.5,
        max_delay=8.0,
        max_total_wait=20.0,
    )

    def operation() -> object:
        return client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": "用一句话解释指数退避。"}],
            temperature=0.2,
            max_tokens=256,
            extra_body=thinking_body(False),
        )

    def report_retry(attempt: int, error: BaseException, delay: float) -> None:
        status = status_code_from_error(error)
        category = f"HTTP {status}" if status is not None else error.__class__.__name__
        print(
            f"Transient {category}; attempt {attempt + 1}/{policy.max_attempts} "
            f"in {delay:.3f}s"
        )

    response = call_with_retry(operation, policy=policy, on_retry=report_retry)
    print_response(response, secrets=[config.api_key])


if __name__ == "__main__":
    run_example(main)
