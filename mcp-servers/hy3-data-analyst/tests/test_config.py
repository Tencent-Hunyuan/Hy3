from pathlib import Path

import pytest

from hy3_data_analyst.config import Settings
from hy3_data_analyst.hy3 import _redact


def test_settings_are_loaded_from_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HY3_API_BASE", "https://hy3.example/v1")
    monkeypatch.setenv("HY3_API_KEY", "test-only-key")
    monkeypatch.setenv("HY3_MODEL", "custom-hy3")
    monkeypatch.setenv("HY3_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HY3_MAX_FILE_BYTES", "2048")
    monkeypatch.setenv("HY3_TIMEOUT_SECONDS", "30")

    result = Settings.from_env()

    assert result.api_base == "https://hy3.example/v1"
    assert result.api_key == "test-only-key"
    assert result.model == "custom-hy3"
    assert result.data_dir == tmp_path.resolve()
    assert result.max_file_bytes == 2048
    assert result.timeout_seconds == 30


def test_invalid_environment_limit_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HY3_MAX_FILE_BYTES", "zero")

    with pytest.raises(ValueError, match="must be an integer"):
        Settings.from_env()


def test_api_key_is_redacted_from_errors() -> None:
    assert _redact("failed with sk-secret", "sk-secret") == "failed with [REDACTED]"
