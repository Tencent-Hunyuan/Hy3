import pytest

from tests.fakes import FakeHy3Client


async def test_returns_queued_replies_in_order() -> None:
    fake = FakeHy3Client(replies=["first", "second"])

    assert await fake.complete("sys", "user1") == "first"
    assert await fake.complete("sys", "user2") == "second"


async def test_records_calls_including_reasoning_effort() -> None:
    fake = FakeHy3Client(replies=["only"])

    await fake.complete("sys prompt", "user prompt", reasoning_effort="high")

    assert fake.calls == [("sys prompt", "user prompt", "high")]


async def test_default_reasoning_effort_recorded_as_no_think() -> None:
    fake = FakeHy3Client(replies=["only"])

    await fake.complete("sys", "user")

    assert fake.calls == [("sys", "user", "no_think")]


async def test_raises_assertion_error_when_replies_exhausted() -> None:
    fake = FakeHy3Client(replies=["only"])
    await fake.complete("sys", "user")

    with pytest.raises(AssertionError):
        await fake.complete("sys", "user")


async def test_raises_injected_error_instead_of_returning_reply() -> None:
    injected = RuntimeError("boom")
    fake = FakeHy3Client(replies=["unused"], error=injected)

    with pytest.raises(RuntimeError, match="boom"):
        await fake.complete("sys", "user")
