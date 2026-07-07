from pathlib import Path

from hy3_code_review_mcp.config import Hy3Settings, load_dotenv_file


def test_load_dotenv_file_sets_missing_values_without_overriding_existing(monkeypatch, tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "HY3_BASE_URL=https://from-dotenv.example/v1",
                "HY3_API_KEY=from-dotenv",
                "HY3_MODEL='hy3-dotenv'",
                "HY3_MAX_TOKENS=2048 # inline comment",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HY3_API_KEY", "from-shell")
    monkeypatch.delenv("HY3_BASE_URL", raising=False)
    monkeypatch.delenv("HY3_MODEL", raising=False)
    monkeypatch.delenv("HY3_MAX_TOKENS", raising=False)

    load_dotenv_file(env_file)

    assert Hy3Settings.from_env().base_url == "https://from-dotenv.example/v1"
    assert Hy3Settings.from_env().api_key == "from-shell"
    assert Hy3Settings.from_env().model == "hy3-dotenv"
    assert Hy3Settings.from_env().max_tokens == 2048


def test_settings_defaults_match_local_hy3(monkeypatch):
    for key in [
        "HY3_BASE_URL",
        "HY3_API_KEY",
        "HY3_MODEL",
        "HY3_TEMPERATURE",
        "HY3_TOP_P",
        "HY3_MAX_TOKENS",
        "HY3_REASONING_EFFORT",
    ]:
        monkeypatch.delenv(key, raising=False)

    settings = Hy3Settings.from_env()

    assert settings.base_url == "http://127.0.0.1:8000/v1"
    assert settings.api_key == "EMPTY"
    assert settings.model == "hy3"
    assert settings.temperature == 0.2
    assert settings.top_p == 1.0
    assert settings.max_tokens == 1600
    assert settings.reasoning_effort == "no_think"


def test_openrouter_settings_fall_back_to_openrouter_api_key(monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("HY3_API_KEY", "EMPTY")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-openrouter")

    assert Hy3Settings.from_env().api_key == "sk-openrouter"


def test_tencent_settings_fall_back_to_hunyuan_api_key(monkeypatch):
    monkeypatch.setenv("HY3_BASE_URL", "https://api.hunyuan.cloud.tencent.com/v1")
    monkeypatch.setenv("HY3_API_KEY", "EMPTY")
    monkeypatch.setenv("HUNYUAN_API_KEY", "sk-hunyuan")

    assert Hy3Settings.from_env().api_key == "sk-hunyuan"
