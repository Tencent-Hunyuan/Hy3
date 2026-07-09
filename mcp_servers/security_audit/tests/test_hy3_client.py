import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from hy3_security_mcp.config import Hy3Config
from hy3_security_mcp.hy3_client import Hy3Client, Hy3ClientError

CAPTURED_BODY_KEY = "body"


def _config() -> Hy3Config:
    return Hy3Config(api_key="sk-test", model="tencent/hy3:free")


def _chat_completion_response(content: str | None, finish_reason: str = "stop") -> dict[str, Any]:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "tencent/hy3:free",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish_reason,
                "logprobs": None,
            }
        ],
    }


def _make_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Hy3Client:
    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return Hy3Client(_config(), http_client=http_client)


async def test_complete_returns_content_verbatim() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(200, json=_chat_completion_response("hello from hy3"))

    client = _make_client(handler)

    result = await client.complete("sys prompt", "user prompt")

    assert result == "hello from hy3"


async def test_complete_sends_expected_request_body_and_default_effort() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured[CAPTURED_BODY_KEY] = json.loads(request.content)
        return httpx.Response(200, json=_chat_completion_response("ok"))

    client = _make_client(handler)

    await client.complete("system text", "user text")

    body = captured[CAPTURED_BODY_KEY]
    assert body["model"] == "tencent/hy3:free"
    assert body["temperature"] == 0.2
    assert body["max_tokens"] == 8192
    assert body["messages"] == [
        {"role": "system", "content": "system text"},
        {"role": "user", "content": "user text"},
    ]
    assert body["chat_template_kwargs"]["reasoning_effort"] == "no_think"


async def test_complete_passes_explicit_reasoning_effort() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured[CAPTURED_BODY_KEY] = json.loads(request.content)
        return httpx.Response(200, json=_chat_completion_response("ok"))

    client = _make_client(handler)

    await client.complete("system text", "user text", reasoning_effort="high")

    assert captured[CAPTURED_BODY_KEY]["chat_template_kwargs"]["reasoning_effort"] == "high"


async def test_complete_raises_hy3_client_error_on_empty_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat_completion_response(None, finish_reason="length"))

    client = _make_client(handler)

    with pytest.raises(Hy3ClientError) as exc_info:
        await client.complete("sys", "user")

    message = str(exc_info.value)
    assert "tencent/hy3:free" in message
    assert "length" in message
