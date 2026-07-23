from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from hy3_data_analyst import hy3
from hy3_data_analyst.config import Settings


@pytest.mark.asyncio
async def test_call_hy3_uses_openai_compatible_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    captured: dict[str, Any] = {}

    class FakeCompletions:
        async def create(self, **kwargs: Any) -> Any:
            captured["request"] = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="grounded answer"))]
            )

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=FakeCompletions())

        async def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr(hy3, "AsyncOpenAI", FakeClient)
    config = Settings(
        api_base="https://hy3.example/v1",
        api_key="test-key",
        model="hy3-test",
        data_dir=tmp_path,
        max_file_bytes=1024,
        timeout_seconds=15,
    )

    answer = await hy3.call_hy3(
        [{"role": "user", "content": "Analyze this"}],
        reasoning_effort="medium",
        settings=config,
    )

    assert answer == "grounded answer"
    assert captured["client"] == {
        "base_url": "https://hy3.example/v1",
        "api_key": "test-key",
        "timeout": 15,
    }
    assert captured["request"]["model"] == "hy3-test"
    assert captured["request"]["messages"] == [{"role": "user", "content": "Analyze this"}]
    assert captured["request"]["extra_body"] == {
        "chat_template_kwargs": {"reasoning_effort": "medium"}
    }
    assert captured["closed"] is True
