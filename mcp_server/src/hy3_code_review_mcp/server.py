"""FastMCP stdio entry point and public tools."""

from __future__ import annotations

import argparse
import logging
import sys
from functools import lru_cache
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, ToolAnnotations
from pydantic import Field

from . import __version__
from .config import ConfigurationError, Settings
from .git_service import DiffSource, GitService, GitServiceError
from .hy3_client import Hy3Client, Hy3ClientError
from .review_service import ReviewService
from .tool_errors import error_result

logger = logging.getLogger(__name__)

RepositoryPath = Annotated[
    str,
    Field(
        description=(
            "Repository path inside HY3_WORKSPACE_ROOT. Relative paths are resolved from the "
            "workspace root; ignored when source='provided'."
        )
    ),
]
DiffSourceInput = Annotated[
    DiffSource,
    Field(
        description=(
            "Select working_tree for unstaged changes, staged for git-added changes, refs for "
            "Git revision comparison, or provided when passing provided_diff directly."
        )
    ),
]
BaseRef = Annotated[
    str | None,
    Field(description="Base commit, branch, or tag. Required only when source='refs'."),
]
TargetRef = Annotated[
    str | None,
    Field(
        description=(
            "Optional target commit, branch, or tag when source='refs'. Omit it to compare "
            "base_ref with the current working tree."
        )
    ),
]
ProvidedDiff = Annotated[
    str | None,
    Field(
        description=(
            "Raw unified diff. Required only when source='provided'; do not include secrets or "
            "unrelated repository content."
        )
    ),
]
Focus = Annotated[
    Literal["all", "correctness", "security", "performance", "maintainability"],
    Field(description="Review all areas or prioritize one quality dimension."),
]
OutputLanguage = Annotated[
    str,
    Field(description="Human language for the result, for example Chinese or English."),
]
TestFramework = Annotated[
    str | None,
    Field(description="Optional preferred test framework, such as pytest or Vitest."),
]

_READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)


@lru_cache(maxsize=1)
def _default_service() -> ReviewService:
    """Create one shared service per process instead of one HTTP client per tool call."""
    settings = Settings.from_env()
    return ReviewService(
        git_service=GitService(settings.workspace_root, settings.max_diff_chars),
        analyzer=Hy3Client(settings),
    )


def create_server(service: ReviewService | None = None) -> FastMCP:
    """Create the server; an injected service keeps tests independent of real credentials."""
    mcp = FastMCP(
        "Hy3 Code Review",
        instructions=(
            "Read-only code review tools powered by Hy3. Use repository paths inside the "
            "configured workspace, or pass a diff directly with source='provided'."
        ),
    )

    def get_service() -> ReviewService:
        return service or _default_service()

    async def execute_tool(**kwargs: Any) -> str | CallToolResult:
        try:
            return await get_service().run(**kwargs)
        except (ConfigurationError, GitServiceError, Hy3ClientError) as exc:
            return error_result(exc)
        except Exception as exc:  # pragma: no cover - defensive protocol boundary
            logger.error("Unexpected MCP tool failure: %s", type(exc).__name__)
            return error_result(exc)

    @mcp.tool(
        title="Review Git Diff",
        annotations=_READ_ONLY_ANNOTATIONS,
        structured_output=False,
    )
    async def review_git_diff(
        repository_path: RepositoryPath = ".",
        source: DiffSourceInput = "working_tree",
        base_ref: BaseRef = None,
        target_ref: TargetRef = None,
        provided_diff: ProvidedDiff = None,
        focus: Focus = "all",
        language: OutputLanguage = "Chinese",
    ) -> str | CallToolResult:
        """Find correctness, security, performance, and maintainability issues in a diff.

        Use this tool when the user asks for a code review or wants defects prioritized. It
        returns Markdown findings with code evidence, severity/impact, confidence, and concrete
        remediation. It does not modify files. For a neutral explanation without defect hunting,
        use explain_code_changes instead.

        Args:
            repository_path: Repository path inside HY3_WORKSPACE_ROOT.
            source: working_tree, staged, refs, or provided.
            base_ref: Required base revision when source is refs.
            target_ref: Optional target revision; omitted means compare base_ref to working tree.
            provided_diff: Required raw unified diff when source is provided.
            focus: Review all areas or prioritize one quality dimension.
            language: Human language requested for the result.
        """
        return await execute_tool(
            task="review",
            repository_path=repository_path,
            source=source,
            base_ref=base_ref,
            target_ref=target_ref,
            provided_diff=provided_diff,
            focus=focus,
            language=language,
            reasoning_effort="high",
        )

    @mcp.tool(
        title="Explain Code Changes",
        annotations=_READ_ONLY_ANNOTATIONS,
        structured_output=False,
    )
    async def explain_code_changes(
        repository_path: RepositoryPath = ".",
        source: DiffSourceInput = "working_tree",
        base_ref: BaseRef = None,
        target_ref: TargetRef = None,
        provided_diff: ProvidedDiff = None,
        language: OutputLanguage = "Chinese",
    ) -> str | CallToolResult:
        """Explain what a diff changes without treating every change as a defect.

        Use this tool for onboarding, change walkthroughs, compatibility analysis, or user-facing
        behavior summaries. It returns grounded Markdown covering purpose, behavior, affected
        components, compatibility, and risks. Use review_git_diff when the primary goal is finding
        actionable defects.

        Args:
            repository_path: Repository path inside HY3_WORKSPACE_ROOT.
            source: working_tree, staged, refs, or provided.
            base_ref: Required base revision when source is refs.
            target_ref: Optional target revision.
            provided_diff: Required raw unified diff when source is provided.
            language: Human language requested for the result.
        """
        return await execute_tool(
            task="explain",
            repository_path=repository_path,
            source=source,
            base_ref=base_ref,
            target_ref=target_ref,
            provided_diff=provided_diff,
            language=language,
            reasoning_effort="low",
        )

    @mcp.tool(
        title="Suggest Test Cases",
        annotations=_READ_ONLY_ANNOTATIONS,
        structured_output=False,
    )
    async def suggest_test_cases(
        repository_path: RepositoryPath = ".",
        source: DiffSourceInput = "working_tree",
        base_ref: BaseRef = None,
        target_ref: TargetRef = None,
        provided_diff: ProvidedDiff = None,
        test_framework: TestFramework = None,
        language: OutputLanguage = "Chinese",
    ) -> str | CallToolResult:
        """Design tests that specifically cover behavior introduced or changed by a diff.

        Use this tool when the user asks what to test or wants a regression plan. It returns
        prioritized Markdown test cases covering normal, boundary, failure, regression, and
        security paths, with setup and expected outcomes grounded in the diff. It suggests tests
        but does not execute or create them.

        Args:
            repository_path: Repository path inside HY3_WORKSPACE_ROOT.
            source: working_tree, staged, refs, or provided.
            base_ref: Required base revision when source is refs.
            target_ref: Optional target revision.
            provided_diff: Required raw unified diff when source is provided.
            test_framework: Optional preferred framework, such as pytest or Vitest.
            language: Human language requested for the result.
        """
        return await execute_tool(
            task="tests",
            repository_path=repository_path,
            source=source,
            base_ref=base_ref,
            target_ref=target_ref,
            provided_diff=provided_diff,
            test_framework=test_framework,
            language=language,
            reasoning_effort="high",
        )

    @mcp.tool(
        title="Generate Pull Request Summary",
        annotations=_READ_ONLY_ANNOTATIONS,
        structured_output=False,
    )
    async def generate_pr_summary(
        repository_path: RepositoryPath = ".",
        source: DiffSourceInput = "working_tree",
        base_ref: BaseRef = None,
        target_ref: TargetRef = None,
        provided_diff: ProvidedDiff = None,
        language: OutputLanguage = "Chinese",
    ) -> str | CallToolResult:
        """Turn a diff into a concise pull request description grounded only in visible changes.

        Use this tool when preparing or reviewing PR documentation. It returns Markdown containing
        a suggested title, change summary, behavior impact, risks, and validation checklist. It
        does not create, update, or submit a pull request.

        Args:
            repository_path: Repository path inside HY3_WORKSPACE_ROOT.
            source: working_tree, staged, refs, or provided.
            base_ref: Required base revision when source is refs.
            target_ref: Optional target revision.
            provided_diff: Required raw unified diff when source is provided.
            language: Human language requested for the result.
        """
        return await execute_tool(
            task="pr_summary",
            repository_path=repository_path,
            source=source,
            base_ref=base_ref,
            target_ref=target_ref,
            provided_diff=provided_diff,
            language=language,
            reasoning_effort="no_think",
        )

    return mcp


mcp = create_server()


def main() -> None:
    """Validate CLI options, then run the local MCP server over stdio."""
    parser = argparse.ArgumentParser(
        prog="hy3-code-review-mcp",
        description="Read-only code review MCP server powered by Hy3.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="validate environment variables and exit without starting the MCP server",
    )
    args = parser.parse_args()

    if args.check_config:
        try:
            settings = Settings.from_env()
        except ConfigurationError as exc:
            parser.error(str(exc))
        print(
            "Configuration valid: "
            f"model={settings.model}, base_url={settings.base_url}, "
            f"workspace_root={settings.workspace_root}",
            file=sys.stderr,
        )
        return

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
