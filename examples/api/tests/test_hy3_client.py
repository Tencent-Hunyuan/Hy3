from __future__ import annotations

from dataclasses import dataclass

import pytest
from hy3_client import (
    Hy3Config,
    call_with_retry,
    is_retryable,
    reasoning_options,
    retry_after_seconds,
    split_message,
    stream_fragments,
    value_from,
)


@dataclass
class ExtraOnly:
    model_extra: dict[str, str]


class FakeHTTPError(Exception):
    def __init__(self, status_code: int, retry_after: str | None = None):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        headers = {} if retry_after is None else {"Retry-After": retry_after}
        self.response = type("Response", (), {"headers": headers})()


def test_config_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HY3_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("HY3_API_KEY", "test-only-key")
    monkeypatch.setenv("HY3_MODEL", "served-hy3")
    monkeypatch.setenv("HY3_TIMEOUT", "45.5")

    config = Hy3Config.from_env()

    assert config.base_url == "https://example.test/v1"
    assert config.api_key == "test-only-key"
    assert config.model == "served-hy3"
    assert config.timeout == 45.5
    assert "test-only-key" not in config.safe_summary()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"base_url": "localhost:8000/v1"}, "absolute"),
        ({"base_url": "https://user:pass@example.test/v1"}, "credentials"),
        ({"timeout": 0}, "greater than zero"),
        ({"api_key": ""}, "non-empty"),
        ({"model": ""}, "non-empty"),
    ],
)
def test_config_rejects_invalid_values(changes: dict[str, object], message: str) -> None:
    values = {
        "base_url": "http://127.0.0.1:8000/v1",
        "api_key": "EMPTY",
        "model": "hy3",
        "timeout": 120.0,
    }
    values.update(changes)
    with pytest.raises(ValueError, match=message):
        Hy3Config(**values).validate()


def test_config_rejects_non_numeric_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HY3_TIMEOUT", "later")
    with pytest.raises(ValueError, match="number of seconds"):
        Hy3Config.from_env()


@pytest.mark.parametrize("effort", ["no_think", "low", "high"])
def test_reasoning_options(effort: str) -> None:
    assert reasoning_options(effort) == {"chat_template_kwargs": {"reasoning_effort": effort}}


def test_reasoning_options_reject_unknown_level() -> None:
    with pytest.raises(ValueError, match="reasoning effort"):
        reasoning_options("maximum")


def test_value_from_supports_extension_fields() -> None:
    assert value_from(ExtraOnly({"reasoning_content": "steps"}), "reasoning_content") == "steps"
    assert value_from({"content": "answer"}, "content") == "answer"


def test_split_message_normalizes_missing_values() -> None:
    assert split_message({"reasoning_content": None, "content": "done"}) == ("", "done")


def test_stream_fragments_skips_metadata_and_empty_chunks() -> None:
    chunks = [
        {"choices": []},
        {"choices": [{"delta": {"role": "assistant"}}]},
        {"choices": [{"delta": {"reasoning_content": "think ", "content": None}}]},
        {"choices": [{"delta": {"content": "answer"}}]},
    ]
    assert list(stream_fragments(chunks)) == [("think ", ""), ("", "answer")]


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(408, True), (429, True), (503, True), (400, False), (401, False), (404, False)],
)
def test_retryable_statuses(status_code: int, expected: bool) -> None:
    assert is_retryable(FakeHTTPError(status_code)) is expected


def test_retry_after_numeric_seconds() -> None:
    assert retry_after_seconds(FakeHTTPError(429, "2.5")) == 2.5


def test_call_with_retry_recovers_and_reports_delay() -> None:
    outcomes = [FakeHTTPError(503), "ok"]
    delays: list[float] = []
    reports: list[tuple[int, float, type[BaseException]]] = []

    def operation() -> str:
        outcome = outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    result = call_with_retry(
        operation,
        attempts=3,
        base_delay=2,
        random_value=lambda: 0.25,
        sleep=delays.append,
        on_retry=lambda attempt, delay, error: reports.append((attempt, delay, type(error))),
    )

    assert result == "ok"
    assert delays == [0.5]
    assert reports == [(1, 0.5, FakeHTTPError)]


def test_call_with_retry_does_not_retry_permanent_failure() -> None:
    calls = 0

    def operation() -> None:
        nonlocal calls
        calls += 1
        raise FakeHTTPError(401)

    with pytest.raises(FakeHTTPError):
        call_with_retry(operation, attempts=4, sleep=lambda _: None)
    assert calls == 1
