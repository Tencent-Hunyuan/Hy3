from __future__ import annotations

import asyncio
import gzip
import json
from dataclasses import replace

import httpx
import pytest

from hy3_ci_copilot.errors import Hy3APIError
from hy3_ci_copilot.hy3_client import Hy3Client


@pytest.mark.asyncio
async def test_native_request_uses_hy3_reasoning_contract(settings) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": " diagnosis "}}]})

    result = await Hy3Client(settings, transport=httpx.MockTransport(handler)).complete(
        system_prompt="system",
        user_prompt="evidence",
        reasoning_effort="high",
    )

    assert result == "diagnosis"
    assert captured["headers"]["authorization"] == "Bearer test-key-not-secret"
    assert captured["headers"]["accept-encoding"] == "identity"
    assert captured["body"]["model"] == "hy3"
    assert captured["body"]["temperature"] == 0.9
    assert captured["body"]["top_p"] == 1.0
    assert captured["body"]["chat_template_kwargs"] == {"reasoning_effort": "high"}
    assert "reasoning" not in captured["body"]


@pytest.mark.asyncio
async def test_successful_response_does_not_expose_key(settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": f"result leaked {settings.api_key}"}}
                ]
            },
        )

    result = await Hy3Client(settings, transport=httpx.MockTransport(handler)).complete(
        system_prompt="system",
        user_prompt="evidence",
        reasoning_effort="high",
    )

    assert settings.api_key not in result
    assert result == "result leaked [REDACTED]"


@pytest.mark.asyncio
async def test_openrouter_request_uses_reasoning_object(settings) -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    openrouter = replace(
        settings,
        base_url="https://openrouter.ai/api/v1",
        api_style="auto",
    )
    await Hy3Client(openrouter, transport=httpx.MockTransport(handler)).complete(
        system_prompt="system",
        user_prompt="evidence",
        reasoning_effort="low",
    )

    assert captured["reasoning"] == {"effort": "low"}
    assert "chat_template_kwargs" not in captured


@pytest.mark.asyncio
async def test_authentication_error_does_not_expose_key(settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text=f"invalid token {settings.api_key}")

    with pytest.raises(Hy3APIError) as error:
        await Hy3Client(settings, transport=httpx.MockTransport(handler)).complete(
            system_prompt="system",
            user_prompt="evidence",
            reasoning_effort="high",
        )

    assert settings.api_key not in str(error.value)
    assert "HY3_API_KEY" in str(error.value)


@pytest.mark.asyncio
async def test_long_key_is_redacted_before_error_detail_is_truncated(settings) -> None:
    long_key = "sensitive-prefix-" + "x" * 600
    long_key_settings = replace(settings, api_key=long_key)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text=f"invalid token {long_key}")

    with pytest.raises(Hy3APIError) as error:
        await Hy3Client(
            long_key_settings, transport=httpx.MockTransport(handler)
        ).complete(
            system_prompt="system",
            user_prompt="evidence",
            reasoning_effort="high",
        )

    assert long_key[:500] not in str(error.value)
    assert "[REDACTED]" in str(error.value)


@pytest.mark.asyncio
async def test_invalid_or_empty_responses_are_rejected(settings) -> None:
    responses = iter(
        [
            httpx.Response(200, text="not-json"),
            httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}),
        ]
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return next(responses)

    client = Hy3Client(settings, transport=httpx.MockTransport(handler))
    with pytest.raises(Hy3APIError, match="invalid"):
        await client.complete(
            system_prompt="system", user_prompt="evidence", reasoning_effort="high"
        )
    with pytest.raises(Hy3APIError, match="empty"):
        await client.complete(
            system_prompt="system", user_prompt="evidence", reasoning_effort="high"
        )


@pytest.mark.asyncio
async def test_timeout_is_reported_without_request_details(settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    with pytest.raises(Hy3APIError, match="timed out") as error:
        await Hy3Client(settings, transport=httpx.MockTransport(handler)).complete(
            system_prompt="system",
            user_prompt="evidence",
            reasoning_effort="high",
        )

    assert settings.api_key not in str(error.value)


@pytest.mark.asyncio
async def test_transport_error_does_not_expose_key(settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            f"transport failed with {settings.api_key}", request=request
        )

    with pytest.raises(Hy3APIError, match="Could not reach") as error:
        await Hy3Client(settings, transport=httpx.MockTransport(handler)).complete(
            system_prompt="system",
            user_prompt="evidence",
            reasoning_effort="high",
        )

    assert settings.api_key not in str(error.value)
    assert error.value.__cause__ is None


@pytest.mark.asyncio
async def test_text_parts_are_supported(settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "part one"},
                                {"type": "text", "text": f" {settings.api_key}"},
                                {"type": "text", "text": " and two"},
                            ]
                        }
                    }
                ]
            },
        )

    result = await Hy3Client(settings, transport=httpx.MockTransport(handler)).complete(
        system_prompt="system",
        user_prompt="evidence",
        reasoning_effort="high",
    )

    assert result == "part one [REDACTED] and two"


@pytest.mark.asyncio
async def test_response_size_is_bounded(settings) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * 257)

    client = Hy3Client(
        settings,
        transport=httpx.MockTransport(handler),
        max_response_bytes=256,
    )

    with pytest.raises(Hy3APIError, match="256-byte safety limit"):
        await client.complete(
            system_prompt="system",
            user_prompt="evidence",
            reasoning_effort="high",
        )


@pytest.mark.asyncio
async def test_timeout_is_a_total_wall_clock_deadline(settings) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.1)
        return httpx.Response(200, json={"choices": [{"message": {"content": "late"}}]})

    short_timeout = replace(settings, timeout_seconds=0.01)
    client = Hy3Client(short_timeout, transport=httpx.MockTransport(handler))

    with pytest.raises(Hy3APIError, match=r"0\.01 seconds"):
        await client.complete(
            system_prompt="system",
            user_prompt="evidence",
            reasoning_effort="high",
        )


@pytest.mark.asyncio
async def test_asyncio_timeout_error_is_wrapped(settings, monkeypatch: pytest.MonkeyPatch) -> None:
    client = Hy3Client(settings)

    async def raise_timeout(**_kwargs) -> str:
        raise asyncio.TimeoutError

    monkeypatch.setattr(client, "_complete_with_retries", raise_timeout)

    with pytest.raises(Hy3APIError, match="timed out") as error:
        await client.complete(
            system_prompt="system",
            user_prompt="evidence",
            reasoning_effort="high",
        )

    assert isinstance(error.value.__cause__, asyncio.TimeoutError)


@pytest.mark.asyncio
async def test_gzip_response_is_not_decompressed_twice(settings) -> None:
    result_text = "compressed result " * 100
    decoded_payload = json.dumps({"choices": [{"message": {"content": result_text}}]}).encode()
    payload = gzip.compress(decoded_payload)
    captured_headers: dict[str, str] = {}

    class HeaderCapturingClient(Hy3Client):
        @staticmethod
        def _extract_content(response: httpx.Response) -> str:
            captured_headers.update(response.headers)
            return Hy3Client._extract_content(response)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=payload,
            headers={
                "Content-Encoding": "gzip",
                "Content-Length": str(len(payload)),
            },
        )

    result = await HeaderCapturingClient(
        settings, transport=httpx.MockTransport(handler)
    ).complete(
        system_prompt="system",
        user_prompt="evidence",
        reasoning_effort="high",
    )

    assert result == result_text.strip()
    assert "content-encoding" not in captured_headers
    assert int(captured_headers["content-length"]) == len(decoded_payload)
    assert int(captured_headers["content-length"]) != len(payload)
