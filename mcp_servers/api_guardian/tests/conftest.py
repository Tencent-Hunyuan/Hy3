from __future__ import annotations

from pathlib import Path

import pytest

from hy3_api_guardian.hy3_client import ModelReply
from hy3_api_guardian.models import Usage
from hy3_api_guardian.settings import Settings


class FakeHy3Client:
    def __init__(self, content: str = "Hy3 grounded analysis") -> None:
        self.content = content
        self.calls: list[tuple[str, str]] = []

    async def complete(self, *, system: str, user: str) -> ModelReply:
        self.calls.append((system, user))
        return ModelReply(
            content=self.content,
            usage=Usage(prompt_tokens=100, completion_tokens=20, total_tokens=120),
        )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        api_key="not-a-real-key",
        base_url="https://tokenhub.tencentmaas.com/v1",
        model="hy3",
        allowed_root=tmp_path.resolve(),
        timeout_seconds=10,
        max_retries=0,
        max_file_bytes=200_000,
        max_model_chars=30_000,
        max_output_tokens=2_000,
        reasoning_effort="high",
    )
