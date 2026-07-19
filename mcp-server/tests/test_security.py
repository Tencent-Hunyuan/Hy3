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
"""No hardcoded secrets anywhere in the shipped code and configs."""

from __future__ import annotations

import re
from pathlib import Path

KEY_PATTERN = re.compile(r"\b(sk|tvly)-[A-Za-z0-9_]{8,}")
API_KEY_LITERAL = re.compile(r"""api_key\s*=\s*["']([^"']+)["']""")
HY3_KEY_LITERAL = re.compile(r"""HY3_API_KEY["']?\s*[:=]\s*["'][^"'$<{][^"']*["']""")

#: Sentinels that are explicitly NOT secrets (offline marker, vLLM "EMPTY").
ALLOWED_API_KEY_LITERALS = {"offline", "EMPTY"}


def _iter_shipped_files(mcp_server_dir: Path):
    for sub in ("src", "scripts", "clients", "examples"):
        base = mcp_server_dir / sub
        if base.is_dir():
            yield from (p for p in base.rglob("*") if p.is_file())
    yield mcp_server_dir / "pyproject.toml"


def test_no_hardcoded_secrets(mcp_server_dir):
    for path in _iter_shipped_files(mcp_server_dir):
        text = path.read_text(encoding="utf-8", errors="replace")
        assert not KEY_PATTERN.search(text), f"key-like string in {path}"


def test_api_key_literals_are_sentinels_only(mcp_server_dir):
    for path in (mcp_server_dir / "src").rglob("*.py"):
        for match in API_KEY_LITERAL.finditer(path.read_text(encoding="utf-8")):
            assert match.group(1) in ALLOWED_API_KEY_LITERALS, (
                f"non-sentinel api_key literal in {path}: {match.group(1)!r}"
            )


def test_hy3_api_key_never_assigned_a_literal(mcp_server_dir):
    """HY3_API_KEY may only be *read* from the environment, never set to a value."""
    for path in (mcp_server_dir / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not HY3_KEY_LITERAL.search(text), f"literal HY3_API_KEY value in {path}"


def test_client_configs_use_env_placeholders(mcp_server_dir):
    """Shipped client configs must reference env vars, not inline key values."""
    for path in (mcp_server_dir / "clients").glob("*"):
        text = path.read_text(encoding="utf-8")
        assert not KEY_PATTERN.search(text), f"key-like string in {path}"
