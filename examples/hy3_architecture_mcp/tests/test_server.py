"""Server-level tests: tool registration, schemas, and error conversion."""

from __future__ import annotations

import asyncio

import pytest

from hy3_architecture_mcp import _runtime
from hy3_architecture_mcp.exceptions import Hy3APIError
from hy3_architecture_mcp.schemas import ClarifyRequirementsOutput
from hy3_architecture_mcp.server import (
    analyze_project_context,
    clarify_requirements,
    mcp,
)

from .conftest import FakeHy3Client

EXPECTED_TOOLS = {
    "clarify_requirements",
    "generate_technical_proposal",
    "review_technical_proposal",
    "create_implementation_plan",
    "analyze_project_context",
}


def test_server_lists_five_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS
    assert len(tools) == 5


def test_every_tool_has_description_and_schema():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    for name, tool in tools.items():
        assert tool.description, f"{name} missing description"
        assert tool.inputSchema and tool.inputSchema.get("type") == "object", name


def test_clarify_schema_constraints_visible():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    mq = tools["clarify_requirements"].inputSchema["properties"]["max_questions"]
    assert mq["minimum"] == 1 and mq["maximum"] == 20 and mq["default"] == 8


def test_plan_team_size_constraint_visible():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    ts = tools["create_implementation_plan"].inputSchema["properties"]["team_size"]
    assert ts["minimum"] == 1


def test_analyze_max_depth_constraint_visible():
    tools = {t.name: t for t in asyncio.run(mcp.list_tools())}
    md = tools["analyze_project_context"].inputSchema["properties"]["max_depth"]
    assert md["minimum"] == 0 and md["maximum"] == 10


async def test_tool_returns_dict_on_success():
    out = ClarifyRequirementsOutput(
        understood_goals=["g"],
        ambiguities=[],
        missing_information=[],
        clarifying_questions=["q"],
        acceptance_criteria=[],
        assumptions=[],
    )
    _runtime._client = FakeHy3Client([out])
    result = await clarify_requirements(requirement="build a KB")
    assert isinstance(result, dict)
    assert result["clarifying_questions"] == ["q"]


async def test_tool_converts_hy3_error_to_runtime_error():
    _runtime._client = FakeHy3Client([Hy3APIError("simulated failure")])
    with pytest.raises(RuntimeError, match="simulated failure"):
        await clarify_requirements(requirement="x")


async def test_analyze_tool_requires_workspace_in_error(monkeypatch):
    # No workspace root -> ConfigurationError -> RuntimeError (user-friendly).
    monkeypatch.delenv("HY3_WORKSPACE_ROOT", raising=False)
    from hy3_architecture_mcp.config import reset_settings_cache

    reset_settings_cache()
    _runtime._client = None
    with pytest.raises(RuntimeError):
        await analyze_project_context(paths=["."])
