"""Run all three tools through a real MCP stdio session and print sanitized evidence."""

from __future__ import annotations

import ast
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _summary(name: str, result: Any) -> dict[str, Any]:
    if result.isError:
        raise RuntimeError(f"{name} returned an MCP tool error")
    structured = result.structuredContent or {}
    summary: dict[str, Any] = {
        "tool": name,
        "model": structured.get("model"),
        "usage": structured.get("usage", {}),
    }
    if name == "audit_openapi":
        summary.update(
            {
                "operation_count": structured.get("operation_count"),
                "local_finding_count": len(structured.get("local_findings", [])),
                "hy3_analysis_chars": len(structured.get("hy3_analysis", "")),
            }
        )
    elif name == "detect_breaking_changes":
        summary.update(
            {
                "breaking_count": structured.get("breaking_count"),
                "warning_count": structured.get("warning_count"),
                "compatible_count": structured.get("compatible_count"),
                "hy3_analysis_chars": len(structured.get("hy3_migration_analysis", "")),
            }
        )
    else:
        generated_code = structured.get("generated_code", "")
        python_syntax_valid = False
        if structured.get("framework") == "pytest" and isinstance(generated_code, str):
            try:
                ast.parse(generated_code)
            except SyntaxError as exc:
                raise RuntimeError("Hy3 generated invalid Python contract-test code") from exc
            python_syntax_valid = True
        summary.update(
            {
                "selected_operations": structured.get("selected_operations", []),
                "generated_code_chars": len(generated_code),
                "generated_code_python_syntax_valid": python_syntax_valid,
            }
        )
    return summary


async def run() -> dict[str, Any]:
    if not os.getenv("HY3_API_KEY"):
        raise RuntimeError("Set HY3_API_KEY in the current environment before running live smoke")

    project_root = Path(__file__).parents[1].resolve()
    env = os.environ.copy()
    env["HY3_ALLOWED_ROOT"] = str(project_root)
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_api_guardian"],
        env=env,
    )

    async with (
        stdio_client(parameters) as (read, write),
        ClientSession(read, write) as session,
    ):
        initialization = await session.initialize()
        tools = await session.list_tools()
        audit = await session.call_tool(
            "audit_openapi",
            {
                "spec_path": str(project_root / "examples" / "insecure-api.yaml"),
                "focus": "security",
            },
        )
        diff = await session.call_tool(
            "detect_breaking_changes",
            {
                "old_spec_path": str(project_root / "examples" / "petstore-v1.yaml"),
                "new_spec_path": str(project_root / "examples" / "petstore-v2-breaking.yaml"),
                "include_compatible": True,
            },
        )
        tests = await session.call_tool(
            "generate_contract_tests",
            {
                "spec_path": str(project_root / "examples" / "petstore-v1.yaml"),
                "framework": "pytest",
                "selected_paths": ["GET /pets/{petId}"],
            },
        )

    return {
        "server": initialization.serverInfo.name,
        "server_version": initialization.serverInfo.version,
        "protocol_version": initialization.protocolVersion,
        "tools": sorted(tool.name for tool in tools.tools),
        "results": [
            _summary("audit_openapi", audit),
            _summary("detect_breaking_changes", diff),
            _summary("generate_contract_tests", tests),
        ],
    }


def main() -> None:
    print(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
