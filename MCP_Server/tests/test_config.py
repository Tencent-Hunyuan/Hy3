from hy3_mcp_server.config import load_settings


def test_load_settings_defaults(monkeypatch):
    monkeypatch.delenv("HY3_BASE_URL", raising=False)
    monkeypatch.delenv("HY3_API_KEY", raising=False)
    monkeypatch.delenv("HY3_MODEL", raising=False)
    monkeypatch.delenv("HY3_DEFAULT_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("HY3_ENABLE_REASONING_EFFORT", raising=False)
    monkeypatch.delenv("HY3_TIMEOUT_SECONDS", raising=False)

    settings = load_settings()

    assert settings.base_url == "https://tokenhub.tencentmaas.com/v1"
    assert settings.api_key == "EMPTY"
    assert settings.model == "hy3"
    assert settings.default_reasoning_effort == "no_think"
    assert settings.enable_reasoning_effort is False
    assert settings.timeout_seconds == 120.0


def test_load_settings_from_env(monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "http://localhost:9000/v1/")
    monkeypatch.setenv("HY3_API_KEY", "secret")
    monkeypatch.setenv("HY3_MODEL", "custom-hy3")
    monkeypatch.setenv("HY3_DEFAULT_REASONING_EFFORT", "high")
    monkeypatch.setenv("HY3_ENABLE_REASONING_EFFORT", "true")
    monkeypatch.setenv("HY3_TIMEOUT_SECONDS", "30")

    settings = load_settings()

    assert settings.base_url == "http://localhost:9000/v1"
    assert settings.api_key == "secret"
    assert settings.model == "custom-hy3"
    assert settings.default_reasoning_effort == "high"
    assert settings.enable_reasoning_effort is True
    assert settings.timeout_seconds == 30.0


def test_invalid_reasoning_effort_falls_back(monkeypatch):
    monkeypatch.setenv("HY3_DEFAULT_REASONING_EFFORT", "invalid")

    assert load_settings().default_reasoning_effort == "no_think"
