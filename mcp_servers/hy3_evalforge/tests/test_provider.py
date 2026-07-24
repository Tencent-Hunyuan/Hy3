from pathlib import Path

import pytest

from hy3_evalforge.errors import ErrorCode, EvalForgeError
from hy3_evalforge.providers.base import ProviderRequest
from hy3_evalforge.providers.fake import FakeProvider
from hy3_evalforge.providers.hy3 import Hy3Provider
from hy3_evalforge.settings import Settings


@pytest.mark.asyncio
async def test_fake_provider_returns_scripted_responses_without_storing_prompts() -> None:
    provider = FakeProvider(['{"answer": 1}'])
    response = await provider.complete(ProviderRequest("system", "untrusted user content", "low"))

    assert response.content == '{"answer": 1}'
    assert provider.request_count == 1
    assert provider.reasoning_efforts == ["low"]
    assert not hasattr(provider, "requests")


@pytest.mark.asyncio
async def test_fake_provider_fails_closed_when_script_exhausted() -> None:
    provider = FakeProvider([])

    with pytest.raises(EvalForgeError) as raised:
        await provider.complete(ProviderRequest("system", "user", "no_think"))

    assert raised.value.code == ErrorCode.PROVIDER_ERROR


class _FakeCompletions:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    async def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        message = type("Message", (), {"content": '{"ok": true}'})()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


@pytest.mark.asyncio
async def test_hy3_provider_uses_frozen_request_parameters(tmp_path: Path) -> None:
    completions = _FakeCompletions()
    client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    settings = Settings.from_environment(
        {"EVALFORGE_ALLOWED_ROOT": str(tmp_path), "HY3_API_KEY": "x"}
    )
    provider = Hy3Provider(settings, client=client)

    response = await provider.complete(ProviderRequest("system", "user", "high"))

    assert response.content == '{"ok": true}'
    assert completions.kwargs is not None
    assert completions.kwargs["temperature"] == 0.9
    assert completions.kwargs["top_p"] == 1.0
    assert completions.kwargs["response_format"] == {"type": "json_object"}
    assert completions.kwargs["extra_body"] == {
        "chat_template_kwargs": {"reasoning_effort": "high"}
    }
