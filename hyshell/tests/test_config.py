# Copyright (C) 2026 Tencent. Licensed under the Apache License, Version 2.0.
# SPDX-License-Identifier: Apache-2.0
"""Backend selection matrix + no-hardcoded-secret guarantee."""

from __future__ import annotations

import re
from pathlib import Path

from hyshell.config import DEFAULT_API_BASE, BackendMode, Settings

ROOT = Path(__file__).resolve().parents[1]


def test_offline_mode_when_no_api_key():
    settings = Settings.from_env({})
    assert settings.mode is BackendMode.FAKE
    assert settings.api_key == "OFFLINE"
    assert settings.is_offline


def test_real_mode_uses_env_base_and_key():
    settings = Settings.from_env(
        {
            "HY3_API_KEY": "sk-not-a-real-key-for-test",
            "HY3_API_BASE": "https://api.hunyuan.cloud.tencent.com/v1",
        }
    )
    assert settings.mode is BackendMode.REAL
    assert settings.api_base == "https://api.hunyuan.cloud.tencent.com/v1"
    assert settings.api_key == "sk-not-a-real-key-for-test"


def test_default_base_is_selfhosted_vllm():
    settings = Settings.from_env({"HY3_API_KEY": "sk-x-test-1234567890"})
    assert settings.api_base == DEFAULT_API_BASE == "http://127.0.0.1:8000/v1"


def test_offline_flag_beats_real_key():
    settings = Settings.from_env({"HY3_API_KEY": "sk-x-test-1234567890"}, offline=True)
    assert settings.mode is BackendMode.FAKE
    assert settings.api_key == "OFFLINE"


def test_offline_env_var_beats_real_key():
    settings = Settings.from_env(
        {"HY3_API_KEY": "sk-x-test-1234567890", "HYSHELL_OFFLINE": "1"}
    )
    assert settings.mode is BackendMode.FAKE


def test_defaults_match_hy3_readme_recommendations():
    settings = Settings.from_env({})
    assert settings.model == "hy3"
    assert settings.temperature == 0.9
    assert settings.top_p == 1.0
    assert settings.request_timeout == 60.0
    assert settings.max_fix_retries == 2


def test_reasoning_effort_only_when_set():
    assert Settings.from_env({}).reasoning_effort is None
    assert Settings.from_env({"HY3_REASONING_EFFORT": "low"}).reasoning_effort == "low"


def test_home_dir_from_env():
    settings = Settings.from_env({"HYSHELL_HOME": "/x/y"})
    assert settings.home_dir == Path("/x/y")


def test_home_dir_tilde_expanded():
    # .env.example documents HYSHELL_HOME=~/.hyshell — the literal ~ must expand
    settings = Settings.from_env({"HYSHELL_HOME": "~/x"})
    assert settings.home_dir == Path.home() / "x"


def test_masked_key_never_reveals_secret():
    real = Settings.from_env({"HY3_API_KEY": "sk-abcdef1234567890"})
    assert "sk-abcdef1234567890" not in real.masked_key()
    fake = Settings.from_env({})
    assert "offline" in fake.masked_key()


def test_no_secret_material_in_source():
    """Scan every shipped text file for realistic key material."""
    suspicious = re.compile(r"sk-[A-Za-z0-9]{20,}|api[_-]?key\s*=\s*['\"][A-Za-z0-9]{16,}")
    scanned = 0
    for pattern in ("src/**/*.py", "demo/*.py", "tests/*.py", "*.md", "*.toml", ".env.example"):
        for path in ROOT.glob(pattern):
            text = path.read_text(encoding="utf-8")
            assert not suspicious.search(text), f"suspicious secret-like string in {path}"
            scanned += 1
    assert scanned >= 10
