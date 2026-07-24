"""Tests for Hy3Client — uses httpx.MockTransport, no real network / key."""
from __future__ import annotations

import httpx
import pytest

from ctxpilot.hy3.client import Hy3Client, Hy3Error


def _mock_client(response_text: str, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        # verify auth header is sent
        assert request.headers.get("Authorization", "").startswith("Bearer ")
        body = request.read().decode()
        assert "reasoning_effort" in body
        return httpx.Response(status, json={"choices": [{"message": {"content": response_text}}]})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_chat_returns_content():
    c = Hy3Client(api_key="k", base_url="http://t", http_client=_mock_client("hello"))
    assert c.chat("hi") == "hello"


def test_chat_requires_key():
    c = Hy3Client(api_key="", base_url="http://t", http_client=_mock_client("x"))
    with pytest.raises(Hy3Error):
        c.chat("hi")


def test_chat_propagates_api_error():
    c = Hy3Client(api_key="k", base_url="http://t", http_client=_mock_client("e", status=500))
    with pytest.raises(Hy3Error):
        c.chat("hi")


def test_chat_network_error_is_wrapped():
    def boom(request):
        raise httpx.ConnectError("nope")

    c = Hy3Client(api_key="k", base_url="http://t", http_client=httpx.Client(transport=httpx.MockTransport(boom)))
    with pytest.raises(Hy3Error):
        c.chat("hi")


def test_chat_malformed_response_raises():
    def handler(request):
        return httpx.Response(200, json={"unexpected": True})

    c = Hy3Client(api_key="k", base_url="http://t", http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(Hy3Error):
        c.chat("hi")
