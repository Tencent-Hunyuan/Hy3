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
"""MCP client #2 — independent raw JSON-RPC stdio client (zero mcp imports).

Uses scripts/raw_stdio_client.py, which implements the MCP stdio wire
format from scratch, to prove the server works without the official SDK on
the client side.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys

from conftest import MCP_SERVER_DIR, SRC_DIR

RAW_CLIENT_PATH = MCP_SERVER_DIR / "scripts" / "raw_stdio_client.py"


def _load_raw_client_module():
    spec = importlib.util.spec_from_file_location("raw_stdio_client", RAW_CLIENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_raw_client_has_zero_mcp_imports():
    source = RAW_CLIENT_PATH.read_text(encoding="utf-8")
    assert re.search(r"^\s*(import|from)\s+mcp\b", source, re.M) is None


def test_raw_jsonrpc_full_flow():
    mod = _load_raw_client_module()
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONPATH": str(SRC_DIR),
        "HY3_MCP_OFFLINE": "1",
        "HY3_MCP_ROOT": str(MCP_SERVER_DIR),
    }
    with mod.RawStdioClient(
        [sys.executable, "-m", "hy3_mcp"], env=env, cwd=str(MCP_SERVER_DIR)
    ) as client:
        init = client.initialize()
        assert init["serverInfo"]["name"] == "hy3-research-assistant"
        assert init["protocolVersion"]

        tools = client.list_tools()["tools"]
        assert {t["name"] for t in tools} == {
            "review_code",
            "ask_docs",
            "analyze_data",
            "deep_research",
            "hy3_status",
        }

        status = client.call_tool("hy3_status")
        assert status.get("isError") is not True
        assert status["structuredContent"]["mode"] == "offline"

        answer = client.call_tool(
            "ask_docs",
            {
                "question": "How do I run it without an API key?",
                "docs_path": "examples/docs",
            },
        )
        assert answer.get("isError") is not True
        assert answer["structuredContent"]["citations"]
