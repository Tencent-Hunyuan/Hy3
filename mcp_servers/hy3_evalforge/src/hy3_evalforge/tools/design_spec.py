"""Registration for the evaluation-specification MCP tool."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from hy3_evalforge.services.spec_designer import SpecDesigner
from hy3_evalforge.tools._runtime import safe_tool_call, workflow_dependencies


def register(server: FastMCP) -> None:
    """Register the evaluation-specification workflow."""

    @server.tool(name="evalforge_design_spec")
    async def evalforge_design_spec(
        project_dir: str,
        goal: str,
        success_criteria: str,
        failure_examples: str | None = None,
        policies: str | None = None,
        output_language: Literal["zh-CN", "en"] = "zh-CN",
        overwrite: bool = False,
    ) -> dict[str, object]:
        """Turn a natural-language quality target into a structured evaluation specification."""

        async def operation() -> object:
            settings, store, provider = workflow_dependencies()
            designer = SpecDesigner(store, provider, extra_secrets=settings.extra_secret_values())
            return await designer.design(
                project_dir=project_dir,
                goal=goal,
                success_criteria=success_criteria,
                failure_examples=failure_examples,
                policies=policies,
                output_language=output_language,
                overwrite=overwrite,
            )

        return await safe_tool_call(operation)
