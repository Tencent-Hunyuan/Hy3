from __future__ import annotations

from pathlib import Path

import pytest

from hy3_api_guardian.errors import ConfigurationError
from hy3_api_guardian.settings import Settings


def test_defaults_are_tokenhub_and_hy3(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for name in (
        "HY3_API_KEY",
        "HY3_BASE_URL",
        "HY3_MODEL",
        "HY3_ALLOWED_ROOT",
        "HY3_REASONING_EFFORT",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env()
    assert settings.base_url == "https://tokenhub.tencentmaas.com/v1"
    assert settings.model == "hy3"
    assert settings.allowed_root == tmp_path.resolve()


def test_rejects_plaintext_remote_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HY3_ALLOWED_ROOT", str(tmp_path))
    monkeypatch.setenv("HY3_BASE_URL", "http://api.example.test/v1")
    with pytest.raises(ConfigurationError, match="HTTPS"):
        Settings.from_env()


def test_allows_plaintext_localhost_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HY3_ALLOWED_ROOT", str(tmp_path))
    monkeypatch.setenv("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
    assert Settings.from_env().base_url == "http://127.0.0.1:8000/v1"


def test_safe_summary_never_contains_api_key(settings: Settings) -> None:
    summary = settings.safe_summary()
    assert settings.api_key not in str(summary)
    assert summary["api_key_present"] is True


def test_require_api_key_has_actionable_error(settings: Settings) -> None:
    without_key = Settings(
        api_key=None,
        base_url=settings.base_url,
        model=settings.model,
        allowed_root=settings.allowed_root,
        timeout_seconds=settings.timeout_seconds,
        max_retries=settings.max_retries,
        max_file_bytes=settings.max_file_bytes,
        max_model_chars=settings.max_model_chars,
        max_output_tokens=settings.max_output_tokens,
        reasoning_effort=settings.reasoning_effort,
    )
    with pytest.raises(ConfigurationError, match="HY3_API_KEY"):
        without_key.require_api_key()
