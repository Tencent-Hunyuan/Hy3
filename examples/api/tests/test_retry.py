from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from common import (
    RetryBudgetExceeded,
    RetryPolicy,
    call_with_retry,
    create_chat_completion,
    retry_after_seconds,
)


class HttpError(Exception):
    def __init__(self, status_code: int, headers: dict[str, str] | None = None) -> None:
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        self.response = SimpleNamespace(status_code=status_code, headers=headers or {})


@pytest.mark.parametrize("status", [400, 401, 402, 403])
def test_permanent_request_and_account_errors_are_not_retried(status: int) -> None:
    attempts = 0

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise HttpError(status)

    with pytest.raises(HttpError):
        call_with_retry(operation, sleep=lambda _delay: None)
    assert attempts == 1


@pytest.mark.parametrize("status", [429, 502, 503, 504])
def test_transient_statuses_are_retried(status: int) -> None:
    attempts = 0
    sleeps: list[float] = []

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise HttpError(status)
        return "ok"

    result = call_with_retry(
        operation,
        policy=RetryPolicy(base_delay=2, max_delay=2),
        sleep=sleeps.append,
        random_fn=lambda: 1.0,
    )
    assert result == "ok"
    assert attempts == 2
    assert sleeps == [2.0]


def test_retry_after_is_respected_without_jitter() -> None:
    attempts = 0
    sleeps: list[float] = []

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise HttpError(429, {"Retry-After": "3.5"})
        return "ok"

    assert (
        call_with_retry(operation, sleep=sleeps.append, random_fn=lambda: 0.0) == "ok"
    )
    assert sleeps == [3.5]


def test_retry_after_accepts_http_date() -> None:
    now = datetime(2026, 7, 17, 8, 0, tzinfo=timezone.utc)
    error = HttpError(429, {"Retry-After": "Fri, 17 Jul 2026 08:00:05 GMT"})

    assert retry_after_seconds(error, now=now) == 5.0


def test_retry_attempts_are_bounded() -> None:
    attempts = 0

    def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise HttpError(503)

    with pytest.raises(HttpError):
        call_with_retry(
            operation,
            policy=RetryPolicy(max_attempts=3, base_delay=0, max_delay=0),
            sleep=lambda _delay: None,
        )
    assert attempts == 3


def test_retry_after_cannot_exceed_total_wait_budget() -> None:
    with pytest.raises(RetryBudgetExceeded):
        call_with_retry(
            lambda: (_ for _ in ()).throw(HttpError(429, {"Retry-After": "60"})),
            policy=RetryPolicy(max_total_wait=5),
            sleep=lambda _delay: None,
        )


@pytest.mark.parametrize("error", [TimeoutError("timeout"), ConnectionError("reset")])
def test_network_and_timeout_errors_are_retried(error: Exception) -> None:
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise error
        return "ok"

    assert call_with_retry(operation, sleep=lambda _delay: None) == "ok"
    assert attempts == 2


def test_chat_completion_helper_retries_transient_gateway_failure() -> None:
    attempts = 0
    retries: list[tuple[int, int, float]] = []

    def create(**kwargs: object) -> dict[str, object]:
        nonlocal attempts
        attempts += 1
        assert kwargs == {"model": "hy3", "messages": []}
        if attempts == 1:
            raise HttpError(429)
        return {"status": "ok"}

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    result = create_chat_completion(
        client,
        policy=RetryPolicy(base_delay=0, max_delay=0),
        on_retry=lambda attempt, error, delay: retries.append(
            (attempt, error.status_code, delay)
        ),
        model="hy3",
        messages=[],
    )

    assert result == {"status": "ok"}
    assert attempts == 2
    assert retries == [(1, 429, 0.0)]
