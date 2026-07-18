"""Hy3 Architecture MCP Server.

Built on the official MCP Python SDK (FastMCP high-level API) over stdio.
Five tools are registered:

  1. clarify_requirements         (core, calls Hy3)
  2. generate_technical_proposal  (core, calls Hy3)
  3. review_technical_proposal   (core, calls Hy3)
  4. create_implementation_plan   (core, calls Hy3)
  5. analyze_project_context     (restricted local file sandbox + Hy3)
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from ._runtime import close_client, logger
from .exceptions import Hy3McpError
from .schemas import (
    DEFAULT_REVIEW_DIMENSIONS,
    AnalyzeProjectContextInput,
    ClarifyRequirementsInput,
    CreateImplementationPlanInput,
    GenerateTechnicalProposalInput,
    ReviewTechnicalProposalInput,
)
from .tools import planning, project_context, proposal, requirements, review


@contextlib.asynccontextmanager
async def _lifespan(_app: FastMCP) -> AsyncIterator[None]:
    try:
        yield
    finally:
        await close_client()


mcp = FastMCP(
    "hy3-architecture",
    instructions=(
        "Hy3-powered technical-proposal review workflow. "
        "Pipeline: clarify_requirements -> generate_technical_proposal -> "
        "review_technical_proposal -> create_implementation_plan. "
        "Use analyze_project_context to feed trusted local files into the pipeline."
    ),
    lifespan=_lifespan,
)


def _explain(exc: Hy3McpError) -> str:
    """Convert a typed Hy3McpError into a concise, actionable message.

    The API key never appears in exception text (see exceptions/hy3_client)."""
    return str(exc)


# ---------------------------------------------------------------------------
# Tool 1 - clarify_requirements
# ---------------------------------------------------------------------------


@mcp.tool()
async def clarify_requirements(
    requirement: Annotated[str, Field(min_length=1)],
    project_context: str | None = None,
    constraints: list[str] | None = None,
    output_language: str = "zh-CN",
    max_questions: Annotated[int, Field(ge=1, le=20)] = 8,
) -> dict:
    """Analyse a fuzzy requirement and surface ambiguities + clarifying questions.

    Returns understood goals, ambiguities, missing information, prioritised
    clarifying questions (<= max_questions), verifiable acceptance criteria,
    and explicit assumptions.
    """
    try:
        result = await requirements.run(
            ClarifyRequirementsInput(
                requirement=requirement,
                project_context=project_context,
                constraints=constraints or [],
                output_language=output_language,
                max_questions=max_questions,
            )
        )
        return result.model_dump()
    except Hy3McpError as exc:
        raise RuntimeError(_explain(exc)) from exc


# ---------------------------------------------------------------------------
# Tool 2 - generate_technical_proposal
# ---------------------------------------------------------------------------


@mcp.tool()
async def generate_technical_proposal(
    requirements: Annotated[str, Field(min_length=1)],
    project_context: str | None = None,
    preferred_stack: list[str] | None = None,
    constraints: list[str] | None = None,
    proposal_depth: Literal["brief", "standard", "detailed"] = "standard",
    output_language: str = "zh-CN",
) -> dict:
    """Generate a reviewable technical proposal from clarified requirements.

    Returns architecture (components/data flow/interfaces), technology choices
    with rationale, at least one alternative, non-functional design, risks and
    open questions.
    """
    try:
        result = await proposal.run(
            GenerateTechnicalProposalInput(
                requirements=requirements,
                project_context=project_context,
                preferred_stack=preferred_stack or [],
                constraints=constraints or [],
                proposal_depth=proposal_depth,
                output_language=output_language,
            )
        )
        return result.model_dump()
    except Hy3McpError as exc:
        raise RuntimeError(_explain(exc)) from exc


# ---------------------------------------------------------------------------
# Tool 3 - review_technical_proposal
# ---------------------------------------------------------------------------


@mcp.tool()
async def review_technical_proposal(
    proposal: Annotated[str, Field(min_length=1)],
    requirements: str | None = None,
    review_dimensions: list[str] | None = None,
    risk_threshold: Literal["low", "medium", "high"] = "medium",
    output_language: str = "zh-CN",
) -> dict:
    """Review a technical proposal across engineering dimensions.

    Returns a verdict (approve/approve_with_changes/reject), a 0-100 score,
    evidence-backed findings with severity, missing decisions and priority
    actions. Defaults to 8 dimensions: requirement_coverage, maintainability,
    scalability, reliability, cost, testability, observability, data_privacy.
    """
    try:
        result = await review.run(
            ReviewTechnicalProposalInput(
                proposal=proposal,
                requirements=requirements,
                review_dimensions=review_dimensions or list(DEFAULT_REVIEW_DIMENSIONS),
                risk_threshold=risk_threshold,
                output_language=output_language,
            )
        )
        return result.model_dump()
    except Hy3McpError as exc:
        raise RuntimeError(_explain(exc)) from exc


# ---------------------------------------------------------------------------
# Tool 4 - create_implementation_plan
# ---------------------------------------------------------------------------


@mcp.tool()
async def create_implementation_plan(
    proposal: Annotated[str, Field(min_length=1)],
    team_size: Annotated[int, Field(ge=1)],
    target_days: int | None = None,
    available_roles: list[str] | None = None,
    output_language: str = "zh-CN",
) -> dict:
    """Turn a reviewed proposal into an executable implementation plan.

    Returns milestones with tasks (id/title/description/dependencies/role/
    effort/deliverables/acceptance criteria), the critical path,
    parallelisable work, delivery risks and a definition of done.
    """
    try:
        result = await planning.run(
            CreateImplementationPlanInput(
                proposal=proposal,
                team_size=team_size,
                target_days=target_days,
                available_roles=available_roles or [],
                output_language=output_language,
            )
        )
        return result.model_dump()
    except Hy3McpError as exc:
        raise RuntimeError(_explain(exc)) from exc


# ---------------------------------------------------------------------------
# Tool 5 - analyze_project_context
# ---------------------------------------------------------------------------


@mcp.tool()
async def analyze_project_context(
    paths: Annotated[list[str], Field(min_length=1)],
    include_content_summary: bool = True,
    max_depth: Annotated[int, Field(ge=0, le=10)] = 2,
    output_language: str = "zh-CN",
) -> dict:
    """Read user-specified local files (inside HY3_WORKSPACE_ROOT) and analyse them.

    Strict sandbox: only files under HY3_WORKSPACE_ROOT are read, with an
    extension allow-list (.md/.txt/.json/.toml/.yaml/.yml/.py/.js/.ts/.tsx/
    .jsx/.java/.go/.rs). Secrets, .env, keys, .git, node_modules, dist, build,
    venvs and binaries are refused. Single-file and total-size limits apply.

    Returns detected stack, project structure, important files, constraints,
    architecture observations and warnings.
    """
    try:
        result = await project_context.run(
            AnalyzeProjectContextInput(
                paths=paths,
                include_content_summary=include_content_summary,
                max_depth=max_depth,
                output_language=output_language,
            )
        )
        return result.model_dump()
    except Hy3McpError as exc:
        raise RuntimeError(_explain(exc)) from exc


def create_server() -> FastMCP:
    """Return the configured FastMCP server (used by entry points and tests)."""
    return mcp


def main() -> None:
    """Run the server over stdio (entry point for the CLI script)."""
    logger.info("Starting Hy3 Architecture MCP Server (stdio)")
    mcp.run()
