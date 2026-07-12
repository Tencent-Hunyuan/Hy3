from __future__ import annotations

import pytest

from hy3_ci_copilot.config import Settings
from hy3_ci_copilot.errors import ConfigurationError


def test_api_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HY3_API_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="HY3_API_KEY is required"):
        Settings.from_env()


def test_api_key_must_be_safe_for_http_headers(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    malformed_key = "TOP_SECRET_KEY\nbad"
    monkeypatch.setenv("HY3_API_KEY", malformed_key)
    monkeypatch.setenv("HY3_ALLOWED_ROOTS", str(tmp_path))

    with pytest.raises(ConfigurationError, match="valid in an HTTP header") as error:
        Settings.from_env()

    assert malformed_key not in str(error.value)


def test_openrouter_is_detected(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("HY3_API_KEY", "secret")
    monkeypatch.setenv("HY3_BASE_URL", "https://openrouter.ai/api/v1/")
    monkeypatch.setenv("HY3_ALLOWED_ROOTS", str(tmp_path))

    settings = Settings.from_env()

    assert settings.base_url == "https://openrouter.ai/api/v1"
    assert settings.resolved_api_style == "openrouter"


@pytest.mark.parametrize(
    "url",
    [
        "localhost:8000/v1",
        "file:///tmp/api",
        "https://user:pass@example.test/v1",
        "https://example.test/v1?key=secret",
    ],
)
def test_invalid_base_urls_are_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path, url: str
) -> None:
    monkeypatch.setenv("HY3_API_KEY", "secret")
    monkeypatch.setenv("HY3_BASE_URL", url)
    monkeypatch.setenv("HY3_ALLOWED_ROOTS", str(tmp_path))

    with pytest.raises(ConfigurationError, match="HY3_BASE_URL"):
        Settings.from_env()
