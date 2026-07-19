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
"""Shared pytest fixtures: src/ on sys.path, scrubbed env, offline deps."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

MCP_SERVER_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = MCP_SERVER_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

_SCRUB_PREFIXES = ("HY3_", "TAVILY_")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never inherit HY3_*/TAVILY_* from the outer shell."""
    for key in list(os.environ):
        if key.startswith(_SCRUB_PREFIXES):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def mcp_server_dir() -> Path:
    return MCP_SERVER_DIR


@pytest.fixture
def examples_dir() -> Path:
    return MCP_SERVER_DIR / "examples"


@pytest.fixture
def offline_settings():
    from hy3_mcp.settings import Settings

    return Settings.from_env(
        {"HY3_MCP_OFFLINE": "1", "HY3_MCP_ROOT": str(MCP_SERVER_DIR)}
    )


@pytest.fixture
def offline_deps(offline_settings):
    from hy3_mcp.hy3_client import Hy3Client
    from hy3_mcp.sources.files import SafeFileReader
    from hy3_mcp.tools import ToolDeps

    return ToolDeps(
        settings=offline_settings,
        client=Hy3Client(offline_settings),
        reader=SafeFileReader(offline_settings.root),
    )


@pytest.fixture
def offline_app(offline_settings):
    from hy3_mcp.server import build_app

    return build_app(offline_settings)
