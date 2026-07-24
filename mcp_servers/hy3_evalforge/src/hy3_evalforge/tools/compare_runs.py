"""Registration for the blinded baseline/candidate comparison MCP tool."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from hy3_evalforge.services.run_comparator import RunComparator
from hy3_evalforge.tools._runtime import safe_tool_call, workflow_dependencies


def register(server: FastMCP) -> None:
    """Register the scorecard-comparison workflow."""

    @server.tool(name="evalforge_compare_runs")
    async def evalforge_compare_runs(
        project_dir: str,
        baseline_run: str,
        candidate_run: str,
        mode: Literal["fast", "balanced", "rigorous"] = "rigorous",
        practical_delta: float = 3.0,
        allow_expensive: bool = False,
        overwrite: bool = False,
    ) -> dict[str, object]:
        """Blindly compare two scored runs and generate a regression conclusion."""

        async def operation() -> object:
            settings, store, provider = workflow_dependencies()
            return await RunComparator(
                store,
                provider,
                max_calls=settings.max_model_calls,
                extra_secrets=settings.extra_secret_values(),
            ).compare_with_pairwise(
                project_dir=project_dir,
                baseline_run=baseline_run,
                candidate_run=candidate_run,
                mode=mode,
                practical_delta=practical_delta,
                allow_expensive=allow_expensive,
                overwrite=overwrite,
            )

        return await safe_tool_call(operation)
