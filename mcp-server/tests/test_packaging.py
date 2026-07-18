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
"""One-command install metadata: console script, deps, entry point."""

from __future__ import annotations

import json

try:
    import tomllib  # Python 3.11+
except ImportError:  # Python 3.10: fall back to the tomli backport if present
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

import pytest

from hy3_mcp import __version__
from hy3_mcp.server import main


def test_pyproject_metadata(mcp_server_dir):
    if tomllib is None:
        pytest.skip("needs tomllib (Python 3.11+) or the tomli backport")
    with open(mcp_server_dir / "pyproject.toml", "rb") as fh:
        meta = tomllib.load(fh)
    project = meta["project"]
    assert project["name"] == "hy3-mcp"
    assert project["version"] == __version__
    assert project["scripts"]["hy3-mcp"] == "hy3_mcp.server:main"
    assert project["requires-python"] == ">=3.10"
    deps = " ".join(project["dependencies"])
    for needed in ("mcp", "openai", "httpx"):
        assert needed in deps
    assert "pillow" not in deps  # Pillow stays out of the core install…
    assert "pillow" in " ".join(project["optional-dependencies"]["demo"])  # …demo extra only
    assert meta["build-system"]["build-backend"] == "hatchling.build"
    wheel = meta["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["packages"] == ["src/hy3_mcp"]


def test_console_entry_point_version(capsys):
    assert main(["--version"]) == 0
    assert f"hy3-mcp {__version__}" in capsys.readouterr().out


def test_console_entry_point_help_mentions_env(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "HY3_" in out and "stdio" in out


def test_selfcheck_passes_offline(capsys):
    assert main(["--selfcheck"]) == 0
    err = capsys.readouterr().err
    assert "PASS" in err
    assert "5 tools" in err


def test_selfcheck_tool_result_extractor_handles_both_shapes():
    """--selfcheck must survive both documented and current call_tool() shapes."""
    from hy3_mcp.server import _tool_result_dict

    class _Block:
        def __init__(self, text: str) -> None:
            self.text = text

    payload = {"mode": "offline", "model": "hy3"}
    # current SDK: (content_blocks, structured_output) tuple
    assert _tool_result_dict(([_Block("ignored")], payload)) == payload
    # documented/older SDK: plain list of content blocks carrying JSON text
    assert _tool_result_dict([_Block(json.dumps(payload))]) == payload
    # tuple without structured output falls back to parsing the content list
    assert _tool_result_dict(([_Block(json.dumps(payload))], None)) == payload
    with pytest.raises(TypeError, match="call_tool"):
        _tool_result_dict(42)
