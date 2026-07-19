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
"""MCP client #1 — official Python SDK over stdio against a real subprocess.

Spawns ``python -m hy3_mcp`` exactly like a real MCP client would and runs
initialize / tools/list / tools/call end to end in offline mode.
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from conftest import MCP_SERVER_DIR, SRC_DIR

EXPECTED_TOOLS = {
    "review_code",
    "ask_docs",
    "analyze_data",
    "deep_research",
    "hy3_status",
}


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_mcp"],
        env={
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "PYTHONPATH": str(SRC_DIR),
            "HY3_MCP_OFFLINE": "1",
            "HY3_MCP_ROOT": str(MCP_SERVER_DIR),
        },
        cwd=str(MCP_SERVER_DIR),
    )


@asynccontextmanager
async def _session():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def test_initialize_and_list_tools_schema_quality():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "hy3-research-assistant"
            assert init.protocolVersion  # negotiated

            tools = (await session.list_tools()).tools
            assert {t.name for t in tools} == EXPECTED_TOOLS

            for tool in tools:
                # acceptance: clear name / description / parameter schemas
                assert tool.description and len(tool.description) >= 20, tool.name
                props = tool.inputSchema.get("properties", {})
                for pname, prop in props.items():
                    if pname == "ctx":
                        continue
                    assert prop.get("description"), f"{tool.name}.{pname} lacks description"
                # every tool returns a structured pydantic model
                assert tool.outputSchema is not None, tool.name


async def test_call_every_tool_offline():
    async with _session() as session:
        before = await session.call_tool("hy3_status", {})
        assert before.isError is False
        assert before.structuredContent["mode"] == "offline"
        assert before.structuredContent["api_key_present"] is False
        assert before.structuredContent["usage"]["calls"] == 0

        review = await session.call_tool(
            "review_code", {"path": "examples/diffs/demo.diff"}
        )
        assert review.isError is False
        assert review.structuredContent["stats"]["hunks"] == 2
        assert len(review.structuredContent["heuristic_flags"]) == 5
        assert "OFFLINE DEMO MODE" in review.structuredContent["markdown"]

        docs = await session.call_tool(
            "ask_docs",
            {
                "question": "What is the context length of Hy3?",
                "docs_path": "examples/docs",
            },
        )
        assert docs.isError is False
        assert docs.structuredContent["citations"], "expected at least one citation"
        assert "256K" in docs.structuredContent["markdown"]

        data = await session.call_tool(
            "analyze_data", {"path": "examples/data/sales_sample.csv"}
        )
        assert data.isError is False
        assert data.structuredContent["profile"]["rows"] == 30
        assert data.structuredContent["chart_suggestions"]

        research = await session.call_tool(
            "deep_research", {"topic": "Hy3 agent capabilities", "max_sources": 2}
        )
        assert research.isError is False
        assert research.structuredContent["search_provider"] == "offline"
        assert len(research.structuredContent["evidence"]) == 2

        after = await session.call_tool("hy3_status", {})
        assert after.structuredContent["usage"]["calls"] == 4  # 4 LLM-backed calls


async def test_tool_error_is_clean_over_stdio():
    async with _session() as session:
        result = await session.call_tool(
            "review_code", {"path": "../../../etc/passwd"}
        )
        assert result.isError is True
        text = " ".join(c.text for c in result.content if c.type == "text")
        assert "sandbox" in text
