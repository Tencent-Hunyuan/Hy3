"""Tests for configuration loading and validation."""

from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from hy3_architecture_mcp.config import Settings, load_settings, reset_settings_cache
from hy3_architecture_mcp.exceptions import ConfigurationError


def _set_env(monkeypatch, **overrides):
    base = {
        "HY3_API_KEY": "EMPTY",
        "HY3_BASE_URL": "http://127.0.0.1:8000/v1",
        "HY3_MODEL": "hy3",
        "HY3_REASONING_EFFORT": "high",
        "HY3_TIMEOUT_SECONDS": "60",
        "HY3_MAX_RETRIES": "2",
        "HY3_WORKSPACE_ROOT": "",
        "HY3_MAX_FILE_SIZE_BYTES": "1048576",
        "HY3_MAX_TOTAL_SIZE_BYTES": "5242880",
    }
    base.update({k: str(v) for k, v in overrides.items()})
    for k, v in base.items():
        if v == "":
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    reset_settings_cache()


def test_loads_with_defaults(monkeypatch):
    _set_env(monkeypatch)
    s = load_settings()
    assert s.api_key.get_secret_value() == "EMPTY"
    assert s.base_url == "http://127.0.0.1:8000/v1"
    assert s.model == "hy3"
    assert s.timeout_seconds == 60
    assert s.max_retries == 2
    assert s.workspace_root is None


def test_base_url_trailing_slash_stripped(monkeypatch):
    _set_env(monkeypatch, HY3_BASE_URL="http://x:8000/v1///")
    assert load_settings().base_url == "http://x:8000/v1"


def test_workspace_root_resolved_to_absolute(monkeypatch, tmp_path):
    _set_env(monkeypatch, HY3_WORKSPACE_ROOT=str(tmp_path))
    root = load_settings().workspace_root
    assert root is not None
    assert root.is_absolute()
    assert root == tmp_path.resolve()


def test_missing_required_when_workspace_used(monkeypatch):
    _set_env(monkeypatch, HY3_WORKSPACE_ROOT="")
    s = load_settings()
    with pytest.raises(ConfigurationError):
        s.require_workspace_root()


def test_invalid_timeout(monkeypatch):
    _set_env(monkeypatch, HY3_TIMEOUT_SECONDS="0")
    with pytest.raises(ConfigurationError):
        load_settings()
    _set_env(monkeypatch, HY3_TIMEOUT_SECONDS="601")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_invalid_retries(monkeypatch):
    _set_env(monkeypatch, HY3_MAX_RETRIES="-1")
    with pytest.raises(ConfigurationError):
        load_settings()
    _set_env(monkeypatch, HY3_MAX_RETRIES="11")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_invalid_reasoning_effort(monkeypatch):
    _set_env(monkeypatch, HY3_REASONING_EFFORT="garbage")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_invalid_size_limits(monkeypatch):
    _set_env(monkeypatch, HY3_MAX_FILE_SIZE_BYTES="0")
    with pytest.raises(ConfigurationError):
        load_settings()
    _set_env(monkeypatch, HY3_MAX_TOTAL_SIZE_BYTES="-5")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_settings_validated_directly():
    s = Settings(timeout_seconds=1, max_retries=1)
    assert isinstance(s.api_key, SecretStr)
    # SecretStr must not reveal its value in repr.
    assert "EMPTY" not in repr(s.api_key) or "***" in repr(s.api_key)


def test_non_numeric_timeout(monkeypatch):
    _set_env(monkeypatch, HY3_TIMEOUT_SECONDS="abc")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_env_not_set_when_unset(monkeypatch):
    # Simulate a completely fresh environment: variables absent.
    for k in list(os.environ):
        if k.startswith("HY3_"):
            monkeypatch.delenv(k, raising=False)
    reset_settings_cache()
    s = load_settings()
    assert s.api_key.get_secret_value() == "EMPTY"
    assert s.base_url == "http://127.0.0.1:8000/v1"
