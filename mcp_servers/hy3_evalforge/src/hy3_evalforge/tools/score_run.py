"""Registration for the single-run scoring MCP tool."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from hy3_evalforge.services.run_scorer import RunScorer
from hy3_evalforge.tools._runtime import safe_tool_call, workflow_dependencies


def register(server: FastMCP) -> None:
    """Register the single-run scoring workflow."""

    @server.tool(name="evalforge_score_run")
    async def evalforge_score_run(
        project_dir: str,
        run_name: str,
        responses_path: str,
        mode: Literal["fast", "balanced", "rigorous"] = "balanced",
        allow_expensive: bool = False,
        overwrite: bool = False,
    ) -> dict[str, object]:
        """Apply hard rules and Hy3 semantic scoring to one JSONL run."""

        async def operation() -> object:
            settings, store, provider = workflow_dependencies()
            scorer = RunScorer(
                store,
                provider,
                max_calls=settings.max_model_calls,
                extra_secrets=settings.extra_secret_values(),
            )
            return await scorer.score(
                project_dir=project_dir,
                run_name=run_name,
                responses_path=responses_path,
                mode=mode,
                allow_expensive=allow_expensive,
                overwrite=overwrite,
            )

        return await safe_tool_call(operation)
