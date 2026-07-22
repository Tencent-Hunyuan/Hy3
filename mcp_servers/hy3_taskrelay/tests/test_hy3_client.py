import json

import httpx
import pytest

from hy3_taskrelay.config import Settings
from hy3_taskrelay.errors import Hy3APIError
from hy3_taskrelay.hy3_client import Hy3Client


def settings() -> Settings:
    return Settings.from_env(
        {
            "HY3_API_KEY": "test-key",
            "HY3_BASE_URL": "https://example.test/v1",
            "HY3_MODEL": "hy3",
        }
    )


@pytest.mark.asyncio
async def test_429_retries_once_after_retry_after_delay() -> None:
    calls = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"error": {"code": "429006", "message": "capacity"}},
            )
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"ok": True})}}]},
        )

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    client = Hy3Client(
        settings(),
        transport=httpx.MockTransport(handler),
        sleep=record_sleep,
    )

    result = await client.complete([{"role": "user", "content": "Return JSON."}])

    assert json.loads(result) == {"ok": True}
    assert calls == 2
    assert delays == [2.0]


@pytest.mark.asyncio
async def test_retry_after_http_date_is_honored_with_the_safety_cap() -> None:
    calls = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "Sun, 01 Jan 2040 00:00:00 GMT"},
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": "done"}}]})

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    result = await Hy3Client(
        settings(), transport=httpx.MockTransport(handler), sleep=record_sleep
    ).complete([{"role": "user", "content": "continue"}])

    assert result == "done"
    assert delays == [30.0]


@pytest.mark.asyncio
async def test_503_is_retried_with_a_finite_backoff() -> None:
    calls = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(503, json={"error": {"message": "temporary"}})
        return httpx.Response(200, json={"choices": [{"message": {"content": "done"}}]})

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    result = await Hy3Client(
        settings(), transport=httpx.MockTransport(handler), sleep=record_sleep
    ).complete([{"role": "user", "content": "continue"}])

    assert result == "done"
    assert calls == 3
    assert delays == [0.5, 1.0]


@pytest.mark.asyncio
async def test_network_timeout_stops_after_the_retry_limit() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("do-not-leak-this-detail", request=request)

    async def no_wait(delay: float) -> None:
        return None

    client = Hy3Client(settings(), transport=httpx.MockTransport(handler), sleep=no_wait)

    with pytest.raises(Hy3APIError, match="after limited retries") as caught:
        await client.complete([{"role": "user", "content": "continue"}])

    assert calls == 3
    assert "do-not-leak-this-detail" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 401, 403])
async def test_permanent_client_errors_are_not_retried_or_echoed(status: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status,
            json={"error": {"message": "account secret", "request_id": "private-request-id"}},
        )

    client = Hy3Client(settings(), transport=httpx.MockTransport(handler))

    with pytest.raises(Hy3APIError) as caught:
        await client.complete([{"role": "user", "content": "continue"}])

    assert calls == 1
    assert "account secret" not in str(caught.value)
    assert "private-request-id" not in str(caught.value)


@pytest.mark.asyncio
async def test_invalid_success_envelope_is_reported_without_raw_content() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"private": "do-not-echo"})
    )

    with pytest.raises(Hy3APIError, match="invalid response envelope") as caught:
        await Hy3Client(settings(), transport=transport).complete(
            [{"role": "user", "content": "continue"}]
        )

    assert "do-not-echo" not in str(caught.value)


@pytest.mark.asyncio
async def test_remote_protocol_error_is_retried_without_echoing_details() -> None:
    calls = 0
    marker = "REMOTE_PROTOCOL_LEAK_MARKER"

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.RemoteProtocolError(marker)

    async def no_wait(delay: float) -> None:
        return None

    with pytest.raises(Hy3APIError, match="after limited retries") as caught:
        await Hy3Client(settings(), transport=httpx.MockTransport(handler), sleep=no_wait).complete(
            [{"role": "user", "content": "continue"}]
        )

    assert calls == 3
    assert marker not in str(caught.value)


@pytest.mark.asyncio
async def test_oversized_response_envelope_is_rejected_before_json_parsing() -> None:
    oversized = {
        "padding": "x" * 520_000,
        "choices": [{"message": {"content": "small"}}],
    }
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=oversized))

    with pytest.raises(Hy3APIError, match="transport safety limit"):
        await Hy3Client(settings(), transport=transport).complete(
            [{"role": "user", "content": "continue"}]
        )
