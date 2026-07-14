import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

from hy3_code_review_mcp.git_service import GitService
from hy3_code_review_mcp.review_service import ReviewService
from hy3_code_review_mcp.server import create_server


class FakeAnalyzer:
    async def analyze(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        reasoning_effort: str | None = None,
    ) -> str:
        return f"mock:{reasoning_effort}"


@pytest.mark.asyncio
async def test_server_exposes_four_tools(tmp_path: Path) -> None:
    service = ReviewService(GitService(tmp_path, 10_000), FakeAnalyzer())
    server = create_server(service)

    tools = await server.list_tools()

    assert {tool.name for tool in tools} == {
        "review_git_diff",
        "explain_code_changes",
        "suggest_test_cases",
        "generate_pr_summary",
    }


@pytest.mark.asyncio
async def test_server_calls_review_tool_with_injected_service(tmp_path: Path) -> None:
    service = ReviewService(GitService(tmp_path, 10_000), FakeAnalyzer())
    server = create_server(service)

    result = await server.call_tool(
        "review_git_diff",
        {
            "source": "provided",
            "provided_diff": "diff --git a/a.py b/a.py\n+x = 1",
        },
    )

    assert len(result) == 1
    assert result[0].text == "mock:high"


@pytest.mark.asyncio
async def test_server_returns_structured_error_for_invalid_diff(tmp_path: Path) -> None:
    service = ReviewService(GitService(tmp_path, 10_000), FakeAnalyzer())
    server = create_server(service)

    result = await server.call_tool(
        "review_git_diff",
        {"source": "provided", "provided_diff": ""},
    )

    assert isinstance(result, CallToolResult)
    assert result.isError is True
    assert result.structuredContent == {
        "ok": False,
        "error": {
            "code": "INVALID_DIFF_INPUT",
            "message": "provided_diff is required when source='provided'",
            "suggested_action": "Pass a non-empty unified diff in provided_diff.",
            "retryable": False,
        },
    }
    assert json.loads(result.content[0].text) == result.structuredContent


@pytest.mark.asyncio
async def test_stdio_server_lists_tools() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_code_review_mcp.server"],
    )

    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()

    assert {tool.name for tool in result.tools} == {
        "review_git_diff",
        "explain_code_changes",
        "suggest_test_cases",
        "generate_pr_summary",
    }


@pytest.mark.asyncio
async def test_stdio_tool_error_sets_is_error_and_structured_content(tmp_path: Path) -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_code_review_mcp.server"],
        env={"HY3_ENV_FILE": str(tmp_path / "missing.env")},
    )

    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "review_git_diff",
                {
                    "source": "provided",
                    "provided_diff": "diff --git a/a.py b/a.py\n+x = 1",
                },
            )

    assert result.isError is True
    assert result.structuredContent is not None
    assert result.structuredContent["error"]["code"] == "CONFIGURATION_ERROR"
    assert "--check-config" in result.structuredContent["error"]["suggested_action"]


def test_cli_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "hy3_code_review_mcp.server", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "--check-config" in completed.stdout


def test_cli_checks_config_without_printing_key(tmp_path: Path) -> None:
    env = {
        **os.environ,
        "HY3_API_KEY": "should-not-be-printed",
        "HY3_BASE_URL": "http://localhost:8000/v1",
        "HY3_WORKSPACE_ROOT": str(tmp_path),
    }
    completed = subprocess.run(
        [sys.executable, "-m", "hy3_code_review_mcp.server", "--check-config"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    assert "Configuration valid" in completed.stderr
    assert "should-not-be-printed" not in completed.stdout + completed.stderr


def test_cli_reports_missing_config_without_traceback() -> None:
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"HY3_API_KEY", "HY3_BASE_URL"}
    }
    completed = subprocess.run(
        [sys.executable, "-m", "hy3_code_review_mcp.server", "--check-config"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 2
    assert "HY3_API_KEY is required" in completed.stderr
    assert "Traceback" not in completed.stderr


@pytest.mark.asyncio
async def test_tool_schemas_include_descriptions(tmp_path: Path) -> None:
    service = ReviewService(GitService(tmp_path, 10_000), FakeAnalyzer())
    server = create_server(service)

    tools = await server.list_tools()

    for tool in tools:
        assert tool.title
        assert tool.description
        assert "Use this tool" in tool.description
        assert tool.inputSchema["properties"]["source"]["description"]
        assert tool.inputSchema["properties"]["language"]["description"]
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is True
