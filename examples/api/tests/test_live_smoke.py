from __future__ import annotations

import os

import pytest

from common import ApiConfig, create_chat_completion, create_client, thinking_body

pytestmark = pytest.mark.live


def test_live_basic_chat() -> None:
    if not os.environ.get("HY3_API_KEY"):
        pytest.skip("HY3_API_KEY is not configured; live smoke was not run")
    config = ApiConfig.from_env()
    response = create_chat_completion(
        create_client(config),
        model=config.model,
        messages=[{"role": "user", "content": "Reply with exactly: live-ok"}],
        temperature=0,
        max_tokens=32,
        extra_body=thinking_body(False),
    )
    assert response.choices
    assert response.choices[0].message.content
