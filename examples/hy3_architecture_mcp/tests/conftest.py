"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest

from hy3_architecture_mcp.config import Settings, reset_settings_cache
from hy3_architecture_mcp.hy3_client import Hy3Client


class FakeHy3Client:
    """Stand-in for Hy3Client that returns canned structured results."""

    def __init__(self, responses: list[Any]) -> None:
        # Each entry is either a BaseModel (returned as-is) or an Exception (raised).
        self._responses = list(responses)
        self.calls = 0
        self.last_user_prompt: str | None = None

    async def generate_structured(self, *, system_prompt, user_prompt, response_model):
        self.last_user_prompt = user_prompt
        idx = min(self.calls, len(self._responses) - 1)
        item = self._responses[idx]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item

    async def aclose(self) -> None:
        pass


def make_mocked_client(handler, *, settings: Settings | None = None) -> Hy3Client:
    """Build a real Hy3Client whose HTTP transport is mocked."""
    settings = settings or Settings()
    client = Hy3Client(settings)
    transport = httpx.MockTransport(handler)
    # Replace the underlying async client with one wired to the mock transport.
    client._client = httpx.AsyncClient(
        base_url=settings.base_url,
        transport=transport,
        headers=client._client.headers,
        timeout=httpx.Timeout(settings.timeout_seconds),
    )
    return client


def completion(content: str, model: str = "hy3") -> dict[str, Any]:
    """Build an OpenAI-compatible chat completion payload."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch):
    """Ensure each test starts with a clean settings cache and no leaked env."""
    reset_settings_cache()
    # Disable the cached singleton client between tests.
    from hy3_architecture_mcp import _runtime

    monkeypatch.setattr(_runtime, "_client", None)
    yield
    reset_settings_cache()
    _runtime._client = None


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    return tmp_path.resolve()
