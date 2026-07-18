"""Tests for Hy3Client HTTP, retry and structured-output behaviour.

All tests use httpx.MockTransport — no real network and no real API key.
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest
from pydantic import BaseModel

from hy3_architecture_mcp.config import Settings
from hy3_architecture_mcp.exceptions import (
    Hy3APIError,
    Hy3AuthenticationError,
    Hy3RateLimitError,
    Hy3TimeoutError,
    ModelOutputError,
)
from hy3_architecture_mcp.hy3_client import Hy3Client, _extract_json

from .conftest import completion, make_mocked_client


class OutModel(BaseModel):
    title: str
    items: list[str]


# --- _extract_json --------------------------------------------------------


def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose():
    assert _extract_json('Here is the result:\n{"a": 1}\nDone.') == {"a": 1}


def test_extract_json_empty_raises():
    with pytest.raises(json.JSONDecodeError):
        _extract_json("")


def test_extract_json_array():
    assert _extract_json("prefix [1, 2, 3] suffix") == [1, 2, 3]


# --- success ---------------------------------------------------------------


async def test_generate_structured_success():
    body = json.dumps({"title": "T", "items": ["a", "b"]})
    client = make_mocked_client(lambda req: httpx.Response(200, json=completion(body)))
    result = await client.generate_structured(
        system_prompt="s", user_prompt="u", response_model=OutModel
    )
    assert isinstance(result, OutModel)
    assert result.title == "T"
    await client.aclose()


async def test_generate_structured_fenced_output():
    body = "```json\n" + json.dumps({"title": "T", "items": []}) + "\n```"
    client = make_mocked_client(lambda req: httpx.Response(200, json=completion(body)))
    result = await client.generate_structured(
        system_prompt="s", user_prompt="u", response_model=OutModel
    )
    assert result.title == "T"
    await client.aclose()


async def test_request_body_shape():
    """Verify auth header + chat_template_kwargs are sent."""
    seen = {}

    def handler(req: httpx.Request):
        seen["auth"] = req.headers.get("authorization")
        seen["body"] = req.read()
        return httpx.Response(200, json=completion(json.dumps({"title": "T", "items": []})))

    settings = Settings(api_key="sk-test-123", base_url="http://x/v1", model="hy3")
    client = make_mocked_client(handler, settings=settings)
    await client.generate_structured(system_prompt="s", user_prompt="u", response_model=OutModel)
    body = json.loads(seen["body"])
    assert seen["auth"] == "Bearer sk-test-123"
    assert body["model"] == "hy3"
    assert body["chat_template_kwargs"]["reasoning_effort"] == "high"
    assert body["messages"][0]["role"] == "system"
    await client.aclose()


# --- auth errors -----------------------------------------------------------


async def test_401_raises_auth_error():
    client = make_mocked_client(lambda req: httpx.Response(401, json={"error": "bad"}))
    with pytest.raises(Hy3AuthenticationError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    await client.aclose()


async def test_403_raises_auth_error():
    client = make_mocked_client(lambda req: httpx.Response(403, json={"error": "forbidden"}))
    with pytest.raises(Hy3AuthenticationError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    await client.aclose()


# --- rate limit + retry ---------------------------------------------------


async def test_429_retries_then_raises(monkeypatch):
    # Avoid real sleeping during backoff.
    async def _no_sleep(_):
        return None

    monkeypatch.setattr("hy3_architecture_mcp.hy3_client.asyncio.sleep", _no_sleep)
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(429, json={"error": "slow down"})

    settings = Settings(max_retries=1)
    client = make_mocked_client(handler, settings=settings)
    with pytest.raises(Hy3RateLimitError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    assert calls["n"] == 2  # initial + 1 retry
    await client.aclose()


async def test_5xx_retries_then_succeeds(monkeypatch):
    async def _no_sleep(_):
        return None

    monkeypatch.setattr("hy3_architecture_mcp.hy3_client.asyncio.sleep", _no_sleep)
    states = iter(
        [
            httpx.Response(503),
            httpx.Response(502),
            httpx.Response(200, json=completion(json.dumps({"title": "T", "items": []}))),
        ]
    )

    def handler(req):
        return next(states)

    settings = Settings(max_retries=2)
    client = make_mocked_client(handler, settings=settings)
    result = await client.generate_structured(
        system_prompt="s", user_prompt="u", response_model=OutModel
    )
    assert result.title == "T"
    await client.aclose()


async def test_5xx_exhausted_raises_api_error(monkeypatch):
    async def _no_sleep(_):
        return None

    monkeypatch.setattr("hy3_architecture_mcp.hy3_client.asyncio.sleep", _no_sleep)
    settings = Settings(max_retries=1)
    client = make_mocked_client(lambda req: httpx.Response(500), settings=settings)
    with pytest.raises(Hy3APIError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    await client.aclose()


# --- timeout ---------------------------------------------------------------


async def test_timeout_raises_timeout_error():
    def handler(req: httpx.Request):
        raise httpx.ReadTimeout("timed out", request=req)

    client = make_mocked_client(handler)
    with pytest.raises(Hy3TimeoutError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    await client.aclose()


# --- non-JSON / bad shape --------------------------------------------------


async def test_non_json_response():
    client = make_mocked_client(lambda req: httpx.Response(200, text="<html>nope</html>"))
    with pytest.raises(Hy3APIError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    await client.aclose()


async def test_missing_choices_field():
    client = make_mocked_client(lambda req: httpx.Response(200, json={"foo": "bar"}))
    with pytest.raises(Hy3APIError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    await client.aclose()


# --- structured repair ----------------------------------------------------


async def test_repair_succeeds(monkeypatch, caplog):
    bad = "not json at all"
    good = json.dumps({"title": "Fixed", "items": ["x"]})
    responses = iter([completion(bad), completion(good)])

    def handler(req):
        return httpx.Response(200, json=next(responses))

    client = make_mocked_client(handler)
    with caplog.at_level(logging.WARNING, logger="hy3_architecture_mcp.client"):
        result = await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    assert result.title == "Fixed"
    # Repair log message must not contain the raw bad output verbatim.
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "not json at all" not in joined
    await client.aclose()


async def test_repair_fails_raises_model_output_error(monkeypatch):
    bad1 = "still not json"
    bad2 = "{invalid"
    responses = iter([completion(bad1), completion(bad2)])

    def handler(req):
        return httpx.Response(200, json=next(responses))

    client = make_mocked_client(handler)
    with pytest.raises(ModelOutputError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    await client.aclose()


async def test_schema_mismatch_then_repair(monkeypatch):
    wrong = json.dumps({"title": "T"})  # missing items
    right = json.dumps({"title": "T", "items": ["a"]})
    responses = iter([completion(wrong), completion(right)])

    def handler(req):
        return httpx.Response(200, json=next(responses))

    client = make_mocked_client(handler)
    result = await client.generate_structured(
        system_prompt="s", user_prompt="u", response_model=OutModel
    )
    assert result.items == ["a"]
    await client.aclose()


# --- secret masking in logs ------------------------------------------------


async def test_api_key_never_in_logs(monkeypatch, caplog):
    settings = Settings(api_key="sk-SUPER-SECRET-123")
    client = make_mocked_client(
        lambda req: httpx.Response(401, json={"error": "x"}), settings=settings
    )
    with caplog.at_level(logging.DEBUG), pytest.raises(Hy3AuthenticationError):
        await client.generate_structured(
            system_prompt="s", user_prompt="u", response_model=OutModel
        )
    joined = "\n".join(r.getMessage() for r in caplog.records)
    assert "sk-SUPER-SECRET-123" not in joined
    await client.aclose()


async def test_error_message_excludes_api_key(monkeypatch):
    settings = Settings(api_key="sk-SECRET-99")
    client = make_mocked_client(
        lambda req: httpx.Response(401, json={"error": "x"}), settings=settings
    )
    try:
        with pytest.raises(Hy3AuthenticationError) as ei:
            await client.generate_structured(
                system_prompt="s", user_prompt="u", response_model=OutModel
            )
        assert "sk-SECRET-99" not in str(ei.value)
    finally:
        await client.aclose()


async def test_client_context_manager_closes():
    settings = Settings()
    client = Hy3Client(settings)
    async with client as c:
        assert c is client
    # aclose should have closed the underlying transport without error.
