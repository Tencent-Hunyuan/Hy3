"""Registration for the challenge-case-generation MCP tool."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from hy3_evalforge.services.case_generator import CaseGenerator
from hy3_evalforge.tools._runtime import safe_tool_call, workflow_dependencies


def register(server: FastMCP) -> None:
    """Register the challenge-case generation workflow."""

    @server.tool(name="evalforge_generate_cases")
    async def evalforge_generate_cases(
        project_dir: str,
        categories: str,
        count: int = 12,
        seed: int = 0,
        overwrite: bool = False,
    ) -> dict[str, object]:
        """Generate a risk-diverse challenge-case set from an existing evaluation specification."""

        async def operation() -> object:
            _, store, provider = workflow_dependencies()
            return await CaseGenerator(store, provider).generate(
                project_dir=project_dir,
                categories=categories,
                count=count,
                seed=seed,
                overwrite=overwrite,
            )

        return await safe_tool_call(operation)
