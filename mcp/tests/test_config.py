from __future__ import annotations

import pytest

from hy3_deep_research.config import Config, ConfigError, load_config


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("HUNYUAN_API_KEY", raising=False)
    with pytest.raises(ConfigError):
        load_config()


def test_defaults_when_key_set(hunyuan_env):
    cfg = load_config()
    assert cfg.hunyuan_api_key == "test-key"
    assert cfg.hunyuan_base_url == "https://tokenhub.tencentmaas.com/v1"
    assert cfg.hunyuan_model == "hy3"
    assert cfg.reasoning_format == "top"
    assert cfg.tavily_api_key is None
    assert cfg.search_max_results == 5
    assert cfg.fetch_max_chars == 8000
    assert cfg.research_max_sub_queries == 3
    assert cfg.research_reasoning_effort == "high"


def test_overrides_via_env(monkeypatch):
    monkeypatch.setenv("HUNYUAN_API_KEY", "k")
    monkeypatch.setenv("HUNYUAN_MODEL", "hy3-preview")
    monkeypatch.setenv("HUNYUAN_REASONING_FORMAT", "top")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-xxx")
    monkeypatch.setenv("SEARCH_MAX_RESULTS", "8")
    monkeypatch.setenv("RESEARCH_REASONING_EFFORT", "low")
    cfg = load_config()
    assert cfg.hunyuan_model == "hy3-preview"
    assert cfg.reasoning_format == "top"
    assert cfg.tavily_api_key == "tvly-xxx"
    assert cfg.search_max_results == 8
    assert cfg.research_reasoning_effort == "low"


def test_invalid_reasoning_format_falls_back(hunyuan_env, monkeypatch):
    monkeypatch.setenv("HUNYUAN_REASONING_FORMAT", "nonsense")
    cfg = load_config()
    assert cfg.reasoning_format == "top"


def test_bad_int_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("HUNYUAN_API_KEY", "k")
    monkeypatch.setenv("SEARCH_MAX_RESULTS", "not-a-number")
    cfg = load_config()
    assert cfg.search_max_results == 5
