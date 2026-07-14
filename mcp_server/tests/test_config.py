from pathlib import Path

import pytest

from hy3_code_review_mcp.config import ConfigurationError, Settings


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HY3_API_KEY", "secret")
    monkeypatch.setenv("HY3_BASE_URL", "http://localhost:8000/v1/")
    monkeypatch.setenv("HY3_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("HY3_REASONING_EFFORT", "low")

    settings = Settings.from_env()

    assert settings.api_key == "secret"
    assert settings.base_url == "http://localhost:8000/v1"
    assert settings.workspace_root == tmp_path.resolve()
    assert settings.reasoning_effort == "low"


def test_settings_require_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    monkeypatch.delenv("HY3_ENV_FILE", raising=False)
    monkeypatch.setenv("HY3_BASE_URL", "http://localhost:8000/v1")

    with pytest.raises(ConfigurationError, match="HY3_API_KEY"):
        Settings.from_env()


@pytest.mark.parametrize("value", ["0", "-1", "not-a-number"])
def test_settings_reject_invalid_limit(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("HY3_API_KEY", "secret")
    monkeypatch.setenv("HY3_BASE_URL", "http://localhost:8000/v1")
    monkeypatch.setenv("HY3_MAX_DIFF_CHARS", value)

    with pytest.raises(ConfigurationError, match="HY3_MAX_DIFF_CHARS"):
        Settings.from_env()


def test_settings_load_optional_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "HY3_API_KEY=file-secret\n"
        "HY3_BASE_URL=http://localhost:9000/v1/\n"
        "HY3_MODEL=hy3-file\n"
        "HY3_MAX_DIFF_CHARS=4321\n"
    )
    for name in ("HY3_API_KEY", "HY3_BASE_URL", "HY3_MODEL", "HY3_MAX_DIFF_CHARS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HY3_ENV_FILE", str(env_file))

    settings = Settings.from_env()

    assert settings.api_key == "file-secret"
    assert settings.base_url == "http://localhost:9000/v1"
    assert settings.model == "hy3-file"
    assert settings.max_diff_chars == 4321


def test_process_environment_overrides_env_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("HY3_API_KEY=file-secret\nHY3_BASE_URL=http://file/v1\n")
    monkeypatch.setenv("HY3_ENV_FILE", str(env_file))
    monkeypatch.setenv("HY3_API_KEY", "process-secret")
    monkeypatch.setenv("HY3_BASE_URL", "http://process/v1")

    settings = Settings.from_env()

    assert settings.api_key == "process-secret"
    assert settings.base_url == "http://process/v1"


def test_settings_reject_missing_env_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HY3_ENV_FILE", str(tmp_path / "missing.env"))

    with pytest.raises(ConfigurationError, match="HY3_ENV_FILE"):
        Settings.from_env()
