from __future__ import annotations

from types import SimpleNamespace

import pytest

from hy3_code_review_mcp.config import Hy3Settings
from hy3_code_review_mcp.hy3_client import Hy3Client


def settings() -> Hy3Settings:
    return Hy3Settings(
        base_url="https://gateway.example/v1",
        api_key="test-key",
        model="hy3",
        temperature=0.2,
        top_p=1.0,
        max_tokens=1600,
        reasoning_effort="no_think",
    )


class FakeCompletions:
    def __init__(self, contents):
        self.contents = list(contents)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        content = self.contents.pop(0)
        message = SimpleNamespace(content=content, reasoning=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeSdkClient:
    def __init__(self, contents):
        self.completions = FakeCompletions(contents)
        self.chat = SimpleNamespace(completions=self.completions)


def test_empty_completion_is_retried_with_bounded_timeout():
    sdk_client = FakeSdkClient([None, "## Review\nFound the issue."])
    client = Hy3Client(settings(), sdk_client=sdk_client)

    result = client.complete("Review this diff")

    assert result == "## Review\nFound the issue."
    assert len(sdk_client.completions.calls) == 2
    assert all(call["timeout"] == 30 for call in sdk_client.completions.calls)
    assert "previous response was empty" in (
        sdk_client.completions.calls[1]["messages"][-1]["content"].lower()
    )


def test_repeated_empty_completion_raises_an_error():
    sdk_client = FakeSdkClient([None, "", None])
    client = Hy3Client(settings(), sdk_client=sdk_client)

    with pytest.raises(RuntimeError, match="empty response"):
        client.complete("Review this diff")

    assert len(sdk_client.completions.calls) == 3
