# Copyright 2026 Tencent Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Settings: mode matrix, defaults, secret hygiene."""

from __future__ import annotations

import dataclasses
import json

import pytest

from hy3_mcp.settings import DEFAULT_API_BASE, Settings


@pytest.mark.parametrize(
    ("env", "force_offline", "mode", "api_base", "key_present"),
    [
        # 1. nothing configured -> offline, never crashes
        ({}, False, "offline", DEFAULT_API_BASE, False),
        # 2. explicit offline flag
        ({"HY3_MCP_OFFLINE": "1"}, False, "offline", DEFAULT_API_BASE, False),
        # 3. offline flag beats real credentials
        (
            {
                "HY3_MCP_OFFLINE": "true",
                "HY3_API_BASE": "http://x:1/v1",
                "HY3_API_KEY": "sk-anything",
            },
            False,
            "offline",
            "http://x:1/v1",
            True,
        ),
        # 4. base alone (self-hosted vLLM/SGLang, no key needed) -> real
        ({"HY3_API_BASE": "http://x:1/v1"}, False, "real", "http://x:1/v1", False),
        # 5. key alone (cloud endpoint with default base) -> real
        ({"HY3_API_KEY": "sk-live"}, False, "real", DEFAULT_API_BASE, True),
        # 6. falsy offline flag does not force offline
        (
            {"HY3_MCP_OFFLINE": "0", "HY3_API_BASE": "http://y:2/v1"},
            False,
            "real",
            "http://y:2/v1",
            False,
        ),
        # 7. falsy offline flag + nothing else -> offline fallback
        ({"HY3_MCP_OFFLINE": "no"}, False, "offline", DEFAULT_API_BASE, False),
        # 8. CLI --offline wins over real credentials
        (
            {"HY3_API_BASE": "http://x:1/v1", "HY3_API_KEY": "sk-live"},
            True,
            "offline",
            "http://x:1/v1",
            True,
        ),
        # 9. whitespace-only values are ignored
        ({"HY3_API_BASE": "  ", "HY3_API_KEY": ""}, False, "offline", DEFAULT_API_BASE, False),
    ],
)
def test_mode_matrix(env, force_offline, mode, api_base, key_present):
    s = Settings.from_env(env, force_offline=force_offline)
    assert s.mode == mode
    assert s.api_base == api_base
    assert s.api_key_present is key_present


def test_defaults():
    s = Settings.from_env({})
    assert s.model == "hy3"
    assert s.temperature == 0.9  # upstream README recommendation
    assert s.top_p == 1.0
    assert s.reasoning_effort is None
    assert s.timeout_seconds == 120
    assert s.max_tokens == 2048
    assert s.search_provider == "offline"
    assert s.docs_dir == s.root


def test_overrides(tmp_path):
    docs = tmp_path / "kb"
    docs.mkdir()
    s = Settings.from_env(
        {
            "HY3_MODEL": "hy3-custom",
            "HY3_TEMPERATURE": "0.5",
            "HY3_TOP_P": "0.8",
            "HY3_REASONING_EFFORT": "HIGH",
            "HY3_TIMEOUT_SECONDS": "30",
            "HY3_MAX_TOKENS": "512",
            "HY3_MCP_ROOT": str(tmp_path),
            "HY3_MCP_DOCS_DIR": "kb",  # relative to root
            "HY3_SEARCH_PROVIDER": "Tavily",
        }
    )
    assert s.model == "hy3-custom"
    assert s.temperature == 0.5
    assert s.top_p == 0.8
    assert s.reasoning_effort == "high"
    assert s.timeout_seconds == 30
    assert s.max_tokens == 512
    assert s.root == tmp_path.resolve()
    assert s.docs_dir == docs.resolve()
    assert s.search_provider == "tavily"


def test_invalid_reasoning_effort_rejected():
    with pytest.raises(ValueError, match="HY3_REASONING_EFFORT"):
        Settings.from_env({"HY3_REASONING_EFFORT": "ultra"})


def test_no_secret_in_settings():
    """The raw key never enters Settings — only a presence flag."""
    secret = "sk-SUPERSECRET-1234567890"
    s = Settings.from_env({"HY3_API_KEY": secret})
    assert s.api_key_present is True
    dumped = repr(s) + str(s) + json.dumps(
        {k: str(v) for k, v in dataclasses.asdict(s).items()}
    )
    assert secret not in dumped
    assert "SUPERSECRET" not in dumped
