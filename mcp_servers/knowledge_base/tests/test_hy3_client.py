"""OpenAI-compatible Hy3 客户端契约测试。"""

from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

import hy3_knowledge_mcp.hy3_client as hy3_client_module
from hy3_knowledge_mcp.config import Settings
from hy3_knowledge_mcp.errors import (
    Hy3AuthenticationError,
    Hy3RateLimitError,
    Hy3ResponseError,
    Hy3TimeoutError,
)
from hy3_knowledge_mcp.hy3_client import Hy3Client, answer_schema_chars
from hy3_knowledge_mcp.models import (
    Hy3AnswerPayload,
    Hy3SummaryPayload,
    ReasoningEffort,
)


class FakeCompletions:
    def __init__(self, response: object | tuple[object, ...]) -> None:
        self.repeat_response = not isinstance(response, tuple)
        self.responses = response if isinstance(response, tuple) else (response,)
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        response_index = 0 if self.repeat_response else len(self.calls) - 1
        try:
            response = self.responses[response_index]
        except IndexError:
            raise AssertionError("unexpected extra completion request") from None
        if isinstance(response, Exception):
            raise response
        return response


class FakeOpenAI:
    def __init__(self, response: object) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(response))
        self.close_calls = 0
        self.close_error: Exception | None = None

    async def close(self) -> None:
        self.close_calls += 1
        if self.close_error is not None:
            raise self.close_error


def completion(content: object, *, choices: object | None = None) -> object:
    response_choices = (
        [SimpleNamespace(message=SimpleNamespace(content=content))] if choices is None else choices
    )
    return SimpleNamespace(choices=response_choices)


def settings_for_profile(
    tmp_path,
    profile: str,
    *,
    with_key: bool = True,
    overrides: dict[str, str] | None = None,
) -> Settings:
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    env = {
        "HY3_KB_ROOTS": str(root),
        "HY3_ENDPOINT_PROFILE": profile,
        "HY3_BASE_URL": (
            "http://127.0.0.1:8000/v1" if profile == "local" else "https://example.invalid/v1"
        ),
        "HY3_MODEL": "hy3-test",
    }
    if with_key:
        env["HY3_API_KEY"] = "test-credential"
    if overrides is not None:
        env.update(overrides)
    return Settings.from_env(env)


def answer_json() -> str:
    return '{"answer":"Grounded","used_evidence_ids":["S1"],"insufficient_evidence":false}'


def status_error(error_type: type[Exception], status_code: int) -> Exception:
    request = httpx.Request(
        "POST",
        "https://sensitive-host.invalid/v1/chat/completions",
    )
    response = httpx.Response(
        status_code,
        request=request,
        json={"error": "SENSITIVE_RESPONSE_BODY"},
    )
    return error_type("SENSITIVE_SERVER_MESSAGE", response=response, body=response.json())


def nested_schema_keys(value: object) -> set[str]:
    """递归收集 schema 的所有关键词。"""
    if isinstance(value, dict):
        return set(value).union(*(nested_schema_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(nested_schema_keys(item) for item in value))
    return set()


@pytest.mark.anyio
async def test_answer_uses_strict_json_schema_and_request_settings(tmp_path) -> None:
    fake = FakeOpenAI(completion(answer_json()))
    settings = settings_for_profile(
        tmp_path,
        "openrouter",
        overrides={"HY3_MAX_OUTPUT_TOKENS": "3210"},
    )
    client = Hy3Client(settings, client=fake)
    messages = [{"role": "user", "content": "question"}]
    original_messages = [message.copy() for message in messages]

    payload = await client.answer(
        messages,
        reasoning_effort=ReasoningEffort.HIGH,
    )

    assert payload == Hy3AnswerPayload(
        answer="Grounded",
        used_evidence_ids=("S1",),
        insufficient_evidence=False,
    )
    call = fake.chat.completions.calls[0]
    assert call["model"] == "hy3-test"
    assert call["messages"] is messages
    assert messages == original_messages
    assert call["temperature"] == 0.2
    assert call["top_p"] == 1.0
    assert call["max_completion_tokens"] == 3210
    assert call["extra_body"] == {"reasoning": {"effort": "high"}}
    response_format = call["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    json_schema = response_format["json_schema"]
    assert json_schema["name"] == "hy3_kb_answer"
    assert json_schema["strict"] is True
    schema = json_schema["schema"]
    assert schema["additionalProperties"] is False
    assert not {"minLength", "maxLength"} & nested_schema_keys(schema)
    assert schema["properties"]["used_evidence_ids"]["items"]["pattern"] == (r"^S[1-9][0-9]*$")

    serialized = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    assert answer_schema_chars() == len(serialized)


@pytest.mark.anyio
async def test_summarize_uses_summary_schema_and_payload(tmp_path) -> None:
    fake = FakeOpenAI(completion('{"summary":"Short","used_evidence_ids":["S2"]}'))
    client = Hy3Client(settings_for_profile(tmp_path, "generic"), client=fake)

    payload = await client.summarize(
        [{"role": "user", "content": "summarize"}],
        reasoning_effort=ReasoningEffort.LOW,
    )

    assert payload == Hy3SummaryPayload(summary="Short", used_evidence_ids=("S2",))
    response_format = fake.chat.completions.calls[0]["response_format"]
    assert response_format["json_schema"]["name"] == "hy3_kb_summary"
    schema = response_format["json_schema"]["schema"]
    assert not {"minLength", "maxLength"} & nested_schema_keys(schema)
    assert schema["properties"]["used_evidence_ids"]["items"]["pattern"] == (r"^S[1-9][0-9]*$")


@pytest.mark.anyio
async def test_answer_retries_one_invalid_structured_response(tmp_path) -> None:
    fake = FakeOpenAI((completion("not-json"), completion(answer_json())))
    client = Hy3Client(settings_for_profile(tmp_path, "openrouter"), client=fake)

    payload = await client.answer(
        [{"role": "user", "content": "question"}],
        reasoning_effort=ReasoningEffort.LOW,
    )

    assert payload.answer == "Grounded"
    assert len(fake.chat.completions.calls) == 2
    assert fake.chat.completions.calls[0] == fake.chat.completions.calls[1]


def test_schema_sanitizer_only_removes_explicit_unsupported_keywords() -> None:
    sanitize = getattr(hy3_client_module, "_sanitize_structured_schema", None)
    unsupported = getattr(
        hy3_client_module,
        "UNSUPPORTED_STRUCTURED_SCHEMA_KEYWORDS",
        None,
    )
    source = {
        "type": "object",
        "required": ["value", "ids"],
        "additionalProperties": False,
        "properties": {
            "value": {
                "anyOf": [
                    {"type": "string", "minLength": 1, "format": "uri"},
                    {"type": "null"},
                ]
            },
            "ids": {
                "type": "array",
                "items": {
                    "type": "string",
                    "pattern": r"^S[1-9][0-9]*$",
                    "maxLength": 16,
                },
            },
        },
        "$defs": {
            "label": {
                "type": "string",
                "minLength": 1,
                "maxLength": 20,
                "pattern": r"^[a-z]+$",
            }
        },
    }
    original = deepcopy(source)

    assert callable(sanitize)
    assert unsupported == frozenset({"minLength", "maxLength"})

    sanitized = sanitize(source)

    assert source == original
    assert not {"minLength", "maxLength"} & nested_schema_keys(sanitized)
    assert sanitized["required"] == ["value", "ids"]
    assert sanitized["additionalProperties"] is False
    assert sanitized["properties"]["value"]["anyOf"] == [
        {"type": "string", "format": "uri"},
        {"type": "null"},
    ]
    assert sanitized["properties"]["ids"]["items"]["pattern"] == (r"^S[1-9][0-9]*$")
    assert sanitized["$defs"]["label"]["pattern"] == r"^[a-z]+$"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("effort", "expected"),
    [
        (ReasoningEffort.NONE, "no_think"),
        (ReasoningEffort.LOW, "low"),
        (ReasoningEffort.HIGH, "high"),
    ],
)
async def test_local_profile_maps_reasoning_effort(tmp_path, effort, expected) -> None:
    fake = FakeOpenAI(completion(answer_json()))
    client = Hy3Client(
        settings_for_profile(tmp_path, "local", with_key=False),
        client=fake,
    )

    await client.answer(
        [{"role": "user", "content": "question"}],
        reasoning_effort=effort,
    )

    assert fake.chat.completions.calls[0]["extra_body"] == {
        "chat_template_kwargs": {"reasoning_effort": expected}
    }


def test_remote_profiles_require_api_key(tmp_path) -> None:
    settings = settings_for_profile(tmp_path, "openrouter", with_key=False)

    with pytest.raises(Hy3AuthenticationError, match="HY3_API_KEY") as caught:
        Hy3Client(settings)

    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_constructor_builds_one_reusable_async_client(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, Any]] = []
    fake = FakeOpenAI(completion(answer_json()))

    def fake_constructor(**kwargs: Any) -> FakeOpenAI:
        calls.append(kwargs)
        return fake

    monkeypatch.setattr("hy3_knowledge_mcp.hy3_client.AsyncOpenAI", fake_constructor)
    settings = settings_for_profile(
        tmp_path,
        "openrouter",
        overrides={"HY3_TIMEOUT_SECONDS": "17", "HY3_MAX_RETRIES": "4"},
    )

    client = Hy3Client(settings)

    assert client.client is fake
    assert calls == [
        {
            "api_key": "test-credential",
            "base_url": "https://example.invalid/v1",
            "timeout": 17,
            "max_retries": 4,
        }
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("error", "expected", "message"),
    [
        (
            status_error(AuthenticationError, 401),
            Hy3AuthenticationError,
            "authentication failed",
        ),
        (
            status_error(RateLimitError, 429),
            Hy3RateLimitError,
            "rate limit exceeded",
        ),
        (
            APITimeoutError(
                request=httpx.Request("POST", "https://sensitive-host.invalid/v1/chat/completions")
            ),
            Hy3TimeoutError,
            "timed out or could not connect",
        ),
        (
            APIConnectionError(
                request=httpx.Request("POST", "https://sensitive-host.invalid/v1/chat/completions")
            ),
            Hy3TimeoutError,
            "timed out or could not connect",
        ),
        (
            status_error(InternalServerError, 503),
            Hy3ResponseError,
            "HTTP 503",
        ),
    ],
)
async def test_openai_errors_are_safely_mapped(tmp_path, error, expected, message) -> None:
    fake = FakeOpenAI(error)
    client = Hy3Client(
        settings_for_profile(tmp_path, "openrouter"),
        client=fake,
    )

    with pytest.raises(expected, match=message) as caught:
        await client.answer(
            [{"role": "user", "content": "question"}],
            reasoning_effort=ReasoningEffort.LOW,
        )

    rendered = str(caught.value)
    assert "SENSITIVE" not in rendered
    assert "example.invalid" not in rendered
    assert "test-credential" not in rendered
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert len(fake.chat.completions.calls) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("response", "message"),
    [
        (completion("not-json"), "invalid structured output"),
        (
            completion('{"answer":"","used_evidence_ids":["S1"],"insufficient_evidence":false}'),
            "invalid structured output",
        ),
        (completion(""), "empty structured response"),
        (completion(None), "empty structured response"),
        (completion({"answer": "parsed"}), "invalid structured output"),
        (SimpleNamespace(choices=[]), "invalid structured output"),
        (
            SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace())]),
            "invalid structured output",
        ),
        (SimpleNamespace(), "invalid structured output"),
    ],
)
async def test_invalid_response_shapes_are_safe_errors(tmp_path, response, message) -> None:
    client = Hy3Client(
        settings_for_profile(tmp_path, "openrouter"),
        client=FakeOpenAI(response),
    )

    with pytest.raises(Hy3ResponseError, match=message) as caught:
        await client.answer(
            [{"role": "user", "content": "question"}],
            reasoning_effort=ReasoningEffort.LOW,
        )

    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


@pytest.mark.anyio
async def test_close_is_idempotent_after_success(tmp_path) -> None:
    fake = FakeOpenAI(completion(answer_json()))
    client = Hy3Client(settings_for_profile(tmp_path, "openrouter"), client=fake)

    await client.close()
    await client.close()

    assert fake.close_calls == 1


@pytest.mark.anyio
async def test_close_does_not_swallow_errors_and_can_be_retried(tmp_path) -> None:
    fake = FakeOpenAI(completion(answer_json()))
    fake.close_error = RuntimeError("close failed")
    client = Hy3Client(settings_for_profile(tmp_path, "openrouter"), client=fake)

    with pytest.raises(RuntimeError, match="close failed"):
        await client.close()

    fake.close_error = None
    await client.close()

    assert fake.close_calls == 2
