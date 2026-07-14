from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import httpx
import pytest
from openai import APIStatusError, AsyncOpenAI

from hy3_code_review_mcp.config import Settings
from hy3_code_review_mcp.hy3_client import Hy3Client, Hy3ClientError


class FakeCompletions:
    def __init__(self, content: str | None = "analysis") -> None:
        self.content = content
        self.kwargs: dict[str, Any] = {}

    async def create(self, **kwargs: Any) -> Any:
        self.kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeOpenAI:
    def __init__(self, content: str | None = "analysis") -> None:
        self.completions = FakeCompletions(content)
        self.chat = SimpleNamespace(completions=self.completions)


class FailingCompletions:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    async def create(self, **kwargs: Any) -> Any:
        request = httpx.Request("POST", "https://example.test/v1/chat/completions")
        response = httpx.Response(self.status_code, request=request)
        raise APIStatusError("request failed", response=response, body=None)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        api_key="secret",
        base_url="http://localhost:8000/v1",
        model="hy3-test",
        workspace_root=tmp_path,
    )


@pytest.mark.asyncio
async def test_client_sends_hy3_parameters(tmp_path: Path) -> None:
    fake = FakeOpenAI()
    client = Hy3Client(_settings(tmp_path), client=cast(AsyncOpenAI, fake))

    result = await client.analyze(
        system_prompt="system",
        user_prompt="user",
        reasoning_effort="low",
    )

    assert result == "analysis"
    assert fake.completions.kwargs["model"] == "hy3-test"
    assert fake.completions.kwargs["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert fake.completions.kwargs["extra_body"] == {
        "chat_template_kwargs": {"reasoning_effort": "low"}
    }


@pytest.mark.asyncio
async def test_client_rejects_empty_response(tmp_path: Path) -> None:
    fake = FakeOpenAI(content="")
    client = Hy3Client(_settings(tmp_path), client=cast(AsyncOpenAI, fake))

    with pytest.raises(Hy3ClientError, match="empty text response") as caught:
        await client.analyze(system_prompt="system", user_prompt="user")

    assert caught.value.code == "HY3_RESPONSE_ERROR"
    assert caught.value.retryable is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_code", "retryable"),
    [
        (401, "HY3_AUTH_ERROR", False),
        (429, "HY3_RATE_LIMITED", True),
        (503, "HY3_SERVICE_ERROR", True),
        (400, "HY3_API_ERROR", False),
    ],
)
async def test_client_classifies_api_status_errors(
    tmp_path: Path,
    status_code: int,
    expected_code: str,
    retryable: bool,
) -> None:
    fake = SimpleNamespace(chat=SimpleNamespace(completions=FailingCompletions(status_code)))
    client = Hy3Client(_settings(tmp_path), client=cast(AsyncOpenAI, fake))

    with pytest.raises(Hy3ClientError) as caught:
        await client.analyze(system_prompt="system", user_prompt="user")

    assert caught.value.code == expected_code
    assert caught.value.retryable is retryable
    assert caught.value.suggested_action
