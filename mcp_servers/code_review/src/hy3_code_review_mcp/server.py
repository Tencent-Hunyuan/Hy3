from __future__ import annotations

from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from .config import load_default_dotenv
from .hy3_client import Hy3Client
from .review import (
    review_git_diff_with_client,
    review_patch_with_client,
    suggest_tests_with_client,
)


mcp = FastMCP("Hy3 Code Review MCP", json_response=True)


def _client() -> Hy3Client:
    load_default_dotenv()
    return Hy3Client.from_env()


@mcp.tool()
def review_git_diff(
    repo_path: str,
    base_ref: str = "HEAD",
    target_ref: Optional[str] = None,
    focus: str = "correctness, security, reliability, and tests",
    max_chars: int = 24000,
) -> Dict[str, Any]:
    """Review a local git diff with Hy3.

    Args:
        repo_path: Local repository path to inspect.
        base_ref: Base git ref for `git diff`, for example `main` or `HEAD`.
        target_ref: Optional target ref. When omitted, reviews worktree changes against base_ref.
        focus: Review focus areas, such as security, correctness, performance, or tests.
        max_chars: Maximum diff characters sent to Hy3; longer diffs are truncated with a notice.
    """
    return review_git_diff_with_client(
        repo_path=repo_path,
        base_ref=base_ref,
        target_ref=target_ref,
        focus=focus,
        max_chars=max_chars,
        client=_client(),
    )


@mcp.tool()
def review_patch(
    patch_text: str,
    language: str = "unknown",
    focus: str = "correctness, security, reliability, and tests",
    context: str = "",
) -> Dict[str, Any]:
    """Review a pasted patch or diff with Hy3.

    Args:
        patch_text: Patch, unified diff, or code-change text to review.
        language: Primary language or stack for the patch.
        focus: Review focus areas, such as security, correctness, performance, or tests.
        context: Optional project or business context that helps Hy3 judge the change.
    """
    return review_patch_with_client(
        patch_text=patch_text,
        language=language,
        focus=focus,
        context=context,
        client=_client(),
    )


@mcp.tool()
def suggest_tests(
    diff_text: str,
    test_framework: str = "pytest",
    risk_level: str = "medium",
) -> Dict[str, Any]:
    """Suggest unit, integration, edge-case, and regression tests for a diff.

    Args:
        diff_text: Diff or patch text that needs test coverage.
        test_framework: Preferred test framework, for example pytest, unittest, jest, or go test.
        risk_level: Expected risk level of the change: low, medium, high, or critical.
    """
    return suggest_tests_with_client(
        diff_text=diff_text,
        test_framework=test_framework,
        risk_level=risk_level,
        client=_client(),
    )


def main() -> None:
    load_default_dotenv()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
