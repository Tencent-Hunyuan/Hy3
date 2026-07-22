import asyncio
import json
from pathlib import Path

import httpx
import pytest

from replaylab.hy3 import Hy3Provider, Hy3ProviderError, Hy3Settings
from replaylab.schemas import TaskSpec

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_json(relative_path: str) -> dict[str, object]:
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def task() -> TaskSpec:
    return TaskSpec.model_validate(load_json("fixtures/coding-loop/input.json"))


def assert_provider_compatible_schema(node: object) -> None:
    if isinstance(node, list):
        for item in node:
            assert_provider_compatible_schema(item)
        return
    if not isinstance(node, dict):
        return
    assert "$defs" not in node
    assert "$ref" not in node
    assert "title" not in node
    assert "default" not in node
    if node.get("type") == "object":
        properties = node.get("properties", {})
        assert node.get("additionalProperties") is False
        assert node.get("required") == list(properties)
    for value in node.values():
        assert_provider_compatible_schema(value)


def success_response(*, prompt_tokens: int = 100, completion_tokens: int = 40) -> httpx.Response:
    output = load_json("fixtures/coding-loop/provider-output.json")
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": json.dumps(output)}}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        },
    )


def test_invalid_environment_configuration_does_not_leak_credentials(monkeypatch) -> None:
    secret = "FAKESECRET789"
    monkeypatch.setenv("HY3_API_KEY", "test-key")
    monkeypatch.setenv("HY3_BASE_URL", f"https://user:{secret}@hy3.test/v1")

    with pytest.raises(Hy3ProviderError) as caught:
        Hy3Settings.from_env()

    assert str(caught.value) == "Hy3 provider configuration is invalid"
    assert secret not in str(caught.value)


@pytest.mark.asyncio
async def test_hy3_uses_openai_compatible_structured_output_without_leaking_the_key() -> None:
    seen_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        return success_response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = Hy3Provider(
            Hy3Settings(api_key="unit-test-key", base_url="https://hy3.test/v1"),
            client=client,
        )
        raw = await provider.analyze(task())

    assert json.loads(raw)["finding"]["first_divergence_step_id"] == (
        "step-006-repeat-patch"
    )
    assert len(seen_requests) == 1
    request = seen_requests[0]
    assert request.url == "https://hy3.test/v1/chat/completions"
    assert request.headers["authorization"] == "Bearer unit-test-key"
    payload = json.loads(request.content)
    assert payload["model"] == "hy3"
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is True
    assert_provider_compatible_schema(
        payload["response_format"]["json_schema"]["schema"]
    )
    assert "untrusted data" in payload["messages"][0]["content"].lower()
    assert "hidden chain-of-thought" in payload["messages"][0]["content"].lower()
    assert "do not use later evidence to retroactively" in payload["messages"][0][
        "content"
    ].lower()
    assert '"coverage"' in payload["messages"][0]["content"]
    assert '"finding"' in payload["messages"][0]["content"]
    assert '"replay_plan"' in payload["messages"][0]["content"]
    assert "no extra top-level keys" in payload["messages"][0]["content"].lower()
    assert "covered, violated, or unknown" in payload["messages"][0]["content"]
    assert "stop_conditions item must be a validation_gate object" in payload[
        "messages"
    ][0]["content"]
    assert "strictly after the first divergence" in payload["messages"][0]["content"]
    assert "governing requirement evidence" in payload["messages"][0]["content"]
    assert "delete it from finding.evidence_ids" in payload["messages"][0]["content"]
    assert provider.last_metrics.prompt_tokens == 100
    assert provider.last_metrics.completion_tokens == 40
    assert provider.last_metrics.total_tokens == 140
    assert provider.last_metrics.request_attempts == 1


@pytest.mark.asyncio
async def test_hy3_retries_429_and_5xx_and_respects_retry_after() -> None:
    responses = [
        httpx.Response(429, headers={"Retry-After": "2"}),
        httpx.Response(503),
        success_response(),
    ]
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return responses.pop(0)

    async def record_sleep(delay: float) -> None:
        sleeps.append(delay)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = Hy3Provider(
            Hy3Settings(api_key="test-key", base_url="https://hy3.test/v1"),
            client=client,
            sleep=record_sleep,
        )
        await provider.analyze(task())

    assert sleeps == [2.0, 0.5]
    assert provider.last_metrics.request_attempts == 3


@pytest.mark.asyncio
async def test_exhausted_rate_limit_preserves_only_safe_retry_metadata() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(
            429,
            headers={"Retry-After": "3", "x-request-id": "must-not-leak"},
            json={"error": {"message": "private upstream details"}},
        )

    async def no_sleep(delay: float) -> None:
        del delay

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = Hy3Provider(
            Hy3Settings(api_key="test-key", base_url="https://hy3.test/v1"),
            client=client,
            sleep=no_sleep,
        )
        with pytest.raises(Hy3ProviderError) as caught:
            await provider.analyze(task())

    assert caught.value.status_code == 429
    assert caught.value.retry_after_seconds == 3
    assert "must-not-leak" not in str(caught.value)
    assert "private upstream details" not in str(caught.value)


@pytest.mark.asyncio
async def test_hy3_permanent_error_fails_once_with_a_bounded_message() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        del request
        return httpx.Response(
            401,
            json={"error": {"message": "Authorization: Bearer must-not-leak"}},
            headers={"x-request-id": "private-request-id"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = Hy3Provider(
            Hy3Settings(api_key="test-key", base_url="https://hy3.test/v1"), client=client
        )
        with pytest.raises(Hy3ProviderError, match=r"status 401$") as caught:
            await provider.analyze(task())

    assert calls == 1
    assert "must-not-leak" not in str(caught.value)
    assert "private-request-id" not in str(caught.value)


@pytest.mark.asyncio
async def test_hy3_retries_network_timeouts_but_not_cancellation() -> None:
    timeout_calls = 0
    sleeps: list[float] = []

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        nonlocal timeout_calls
        timeout_calls += 1
        raise httpx.ReadTimeout("private endpoint details", request=request)

    async def record_sleep(delay: float) -> None:
        sleeps.append(delay)

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler)) as client:
        provider = Hy3Provider(
            Hy3Settings(api_key="test-key", base_url="https://hy3.test/v1"),
            client=client,
            sleep=record_sleep,
        )
        with pytest.raises(Hy3ProviderError, match="failed after retries") as caught:
            await provider.analyze(task())

    assert timeout_calls == 3
    assert sleeps == [0.25, 0.5]
    assert "private endpoint details" not in str(caught.value)

    cancel_calls = 0

    async def cancel_handler(request: httpx.Request) -> httpx.Response:
        nonlocal cancel_calls
        cancel_calls += 1
        del request
        raise asyncio.CancelledError

    async with httpx.AsyncClient(transport=httpx.MockTransport(cancel_handler)) as client:
        provider = Hy3Provider(
            Hy3Settings(api_key="test-key", base_url="https://hy3.test/v1"), client=client
        )
        with pytest.raises(asyncio.CancelledError):
            await provider.analyze(task())

    assert cancel_calls == 1


@pytest.mark.asyncio
async def test_controlled_repair_redacts_and_bounds_invalid_output() -> None:
    request_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_bodies.append(json.loads(request.content))
        return success_response()

    invalid_output = {
        "bad": "Authorization: Bearer repair-secret " + ("x" * 30_000),
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = Hy3Provider(
            Hy3Settings(api_key="test-key", base_url="https://hy3.test/v1"), client=client
        )
        await provider.repair(task(), invalid_output, "schema_or_reference_validation_failed")

    body = json.dumps(request_bodies[0])
    assert "repair-secret" not in body
    assert "[REDACTED]" in body
    assert "rewrite the object from scratch" in body.lower()
    assert len(body) < 100_000
