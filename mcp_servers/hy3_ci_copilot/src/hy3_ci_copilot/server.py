from __future__ import annotations

from collections.abc import Awaitable
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from hy3_ci_copilot.errors import (
    AccessDeniedError,
    ConfigurationError,
    Hy3APIError,
    InputFileError,
)
from hy3_ci_copilot.service import (
    build_ci_fix_plan_service,
    compare_ci_runs_service,
    diagnose_ci_failure_service,
    review_ci_workflow_service,
)

mcp = FastMCP(
    "hy3-ci-copilot",
    instructions=(
        "Use these tools to diagnose CI/CD failures from repository-local logs and workflows. "
        "Every tool performs its core analysis with Hy3. Start with diagnose_ci_failure, use "
        "compare_ci_runs when a known-good log exists, and request build_ci_fix_plan before "
        "editing."
    ),
    log_level="ERROR",
)

OutputLanguage = Literal["auto", "zh-CN", "en"]
ReasoningEffort = Literal["no_think", "low", "high"]
READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


async def _tool_result(call: Awaitable[str]) -> str:
    try:
        return await call
    except (ConfigurationError, AccessDeniedError, InputFileError, Hy3APIError) as exc:
        raise ToolError(str(exc)) from None


@mcp.tool(
    name="diagnose_ci_failure",
    title="Diagnose CI Failure",
    description="Diagnose one failed CI run using its log and repository context with Hy3.",
    annotations=READ_ONLY_ANNOTATIONS,
)
async def diagnose_ci_failure(
    log_path: Annotated[
        str,
        Field(
            description="Path to a CI log file inside repository_path.",
            min_length=1,
            max_length=4096,
        ),
    ],
    repository_path: Annotated[
        str,
        Field(
            description="Repository root used for path checks and supporting context.",
            min_length=1,
            max_length=4096,
        ),
    ] = ".",
    focus: Annotated[
        str,
        Field(
            description="Optional component, job, or symptom that should receive extra attention.",
            max_length=4000,
        ),
    ] = "",
    output_language: Annotated[
        OutputLanguage,
        Field(description="Response language: auto, Simplified Chinese, or English."),
    ] = "auto",
    reasoning_effort: Annotated[
        ReasoningEffort,
        Field(description="Hy3 reasoning mode; high is recommended for ambiguous failures."),
    ] = "high",
) -> str:
    """Diagnose one failed CI run using its log plus repository workflow and build context."""
    return await _tool_result(
        diagnose_ci_failure_service(
            log_path=log_path,
            repository_path=repository_path,
            focus=focus,
            output_language=output_language,
            reasoning_effort=reasoning_effort,
        )
    )


@mcp.tool(
    name="compare_ci_runs",
    title="Compare CI Runs",
    description="Compare a failed and a successful CI log with Hy3 to isolate a regression.",
    annotations=READ_ONLY_ANNOTATIONS,
)
async def compare_ci_runs(
    failed_log_path: Annotated[
        str,
        Field(
            description="Path to the failed CI log inside repository_path.",
            min_length=1,
            max_length=4096,
        ),
    ],
    successful_log_path: Annotated[
        str,
        Field(
            description="Path to a comparable successful CI log inside repository_path.",
            min_length=1,
            max_length=4096,
        ),
    ],
    repository_path: Annotated[
        str,
        Field(
            description="Repository root used for path checks and supporting context.",
            min_length=1,
            max_length=4096,
        ),
    ] = ".",
    focus: Annotated[
        str,
        Field(
            description="Optional regression area, dependency, or job to prioritize.",
            max_length=4000,
        ),
    ] = "",
    output_language: Annotated[
        OutputLanguage,
        Field(description="Response language: auto, Simplified Chinese, or English."),
    ] = "auto",
    reasoning_effort: Annotated[
        ReasoningEffort,
        Field(description="Hy3 reasoning mode; high is recommended for regression analysis."),
    ] = "high",
) -> str:
    """Compare successful and failed CI logs to isolate the most likely regression."""
    return await _tool_result(
        compare_ci_runs_service(
            failed_log_path=failed_log_path,
            successful_log_path=successful_log_path,
            repository_path=repository_path,
            focus=focus,
            output_language=output_language,
            reasoning_effort=reasoning_effort,
        )
    )


@mcp.tool(
    name="review_ci_workflow",
    title="Review CI Workflow",
    description="Review a repository-local CI workflow for concrete problems using Hy3.",
    annotations=READ_ONLY_ANNOTATIONS,
)
async def review_ci_workflow(
    workflow_path: Annotated[
        str,
        Field(
            description="Path to a GitHub Actions or other YAML CI workflow inside the repository.",
            min_length=1,
            max_length=4096,
        ),
    ],
    repository_path: Annotated[
        str,
        Field(
            description="Repository root used for path checks and supporting context.",
            min_length=1,
            max_length=4096,
        ),
    ] = ".",
    focus: Annotated[
        str,
        Field(
            description="Optional concern such as caching, matrix jobs, releases, or reliability.",
            max_length=4000,
        ),
    ] = "",
    output_language: Annotated[
        OutputLanguage,
        Field(description="Response language: auto, Simplified Chinese, or English."),
    ] = "auto",
    reasoning_effort: Annotated[
        ReasoningEffort,
        Field(description="Hy3 reasoning mode."),
    ] = "high",
) -> str:
    """Review a CI workflow for concrete correctness and reproducibility problems."""
    return await _tool_result(
        review_ci_workflow_service(
            workflow_path=workflow_path,
            repository_path=repository_path,
            focus=focus,
            output_language=output_language,
            reasoning_effort=reasoning_effort,
        )
    )


@mcp.tool(
    name="build_ci_fix_plan",
    title="Build CI Fix Plan",
    description="Turn a diagnosis into a repository-grounded, read-only fix plan using Hy3.",
    annotations=READ_ONLY_ANNOTATIONS,
)
async def build_ci_fix_plan(
    diagnosis: Annotated[
        str,
        Field(
            description="Diagnosis text from diagnose_ci_failure or compare_ci_runs.",
            min_length=1,
            max_length=100_000,
        ),
    ],
    repository_path: Annotated[
        str,
        Field(
            description="Repository root used to ground the implementation plan.",
            min_length=1,
            max_length=4096,
        ),
    ] = ".",
    constraints: Annotated[
        str,
        Field(
            description="Optional compatibility, rollout, or change-scope constraints.",
            max_length=8000,
        ),
    ] = "",
    output_language: Annotated[
        OutputLanguage,
        Field(description="Response language: auto, Simplified Chinese, or English."),
    ] = "auto",
    reasoning_effort: Annotated[
        ReasoningEffort,
        Field(description="Hy3 reasoning mode."),
    ] = "high",
) -> str:
    """Convert a diagnosis into a repository-grounded, implementation-ready CI fix plan."""
    return await _tool_result(
        build_ci_fix_plan_service(
            diagnosis=diagnosis,
            repository_path=repository_path,
            constraints=constraints,
            output_language=output_language,
            reasoning_effort=reasoning_effort,
        )
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
