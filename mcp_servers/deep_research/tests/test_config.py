from pathlib import Path

from hy3_research_mcp.config import Hy3Settings, ResearchSettings, load_dotenv_file


def test_load_dotenv_file_sets_missing_values_without_overriding_existing(monkeypatch, tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "HY3_BASE_URL=https://from-dotenv.example/v1",
                "HY3_API_KEY=from-dotenv",
                "HY3_MODEL='hy3-dotenv'",
                "HY3_MAX_TOKENS=4096 # inline comment",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HY3_API_KEY", "from-shell")
    monkeypatch.delenv("HY3_BASE_URL", raising=False)
    monkeypatch.delenv("HY3_MODEL", raising=False)
    monkeypatch.delenv("HY3_MAX_TOKENS", raising=False)

    load_dotenv_file(env_file)

    settings = Hy3Settings.from_env()
    assert settings.base_url == "https://from-dotenv.example/v1"
    assert settings.api_key == "from-shell"
    assert settings.model == "hy3-dotenv"
    assert settings.max_tokens == 4096


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
    assert settings.temperature == 0.9
    assert settings.top_p == 1.0
    assert settings.max_tokens == 2048
    assert settings.reasoning_effort == "high"


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


def test_research_settings_defaults_need_no_key(monkeypatch):
    for key in [
        "HY3_SEARCH_API_KEY",
        "TAVILY_API_KEY",
        "BRAVE_API_KEY",
        "HY3_SEARCH_ENGINE",
        "HY3_MAX_SEARCH_RESULTS",
        "HY3_PAGE_TIMEOUT",
        "HY3_MAX_PAGE_CHARS",
        "HY3_USER_AGENT",
    ]:
        monkeypatch.delenv(key, raising=False)
    r = ResearchSettings.from_env()
    assert r.search_engine == "duckduckgo"
    assert r.search_api_key is None
    assert r.max_search_results == 5