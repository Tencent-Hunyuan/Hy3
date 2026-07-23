from __future__ import annotations

import pytest

from hy3_deep_research.config import ConfigurationError, Settings


def test_defaults_do_not_embed_an_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "HY3_API_KEY",
        "HY3_BASE_URL",
        "HY3_MODEL",
        "HY3_REASONING_EFFORT",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env()

    assert settings.api_key is None
    assert settings.base_url == "http://127.0.0.1:8000/v1"
    assert settings.model == "hy3"
    with pytest.raises(ConfigurationError, match="HY3_API_KEY"):
        settings.require_api_key()


def test_local_provider_can_explicitly_use_empty_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HY3_API_KEY", "EMPTY")
    assert Settings.from_env().require_api_key() == "EMPTY"


def test_invalid_reasoning_effort_fails_early(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HY3_REASONING_EFFORT", "maximum")
    with pytest.raises(ConfigurationError, match="HY3_REASONING_EFFORT"):
        Settings.from_env()
