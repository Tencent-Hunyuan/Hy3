"""MCP stdio entrypoint for the Hy3 server."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .tools import answer_question, inspect_data, review_diff


mcp = FastMCP(
    "hy3-mcp-server",
    instructions=(
        "Use Hy3 for code review, document QA, and data insight tasks. "
        "Configure HY3_BASE_URL, HY3_API_KEY, and HY3_MODEL in the MCP client environment."
    ),
)


@mcp.tool()
def hy3_code_review(diff: str, focus: str = "correctness and regressions") -> dict[str, Any]:
    """Review a unified diff with Hy3 and return prioritized findings."""
    return review_diff(diff=diff, focus=focus)


@mcp.tool()
def hy3_document_qa(question: str, documents: list[dict[str, str]]) -> dict[str, Any]:
    """Answer a question from supplied documents and cite document ids."""
    return answer_question(question=question, documents=documents)


@mcp.tool()
def hy3_data_insight(data: str, question: str = "What should I know about this dataset?") -> dict[str, Any]:
    """Analyze CSV or JSON data with Hy3 and return takeaways plus next steps."""
    return inspect_data(data=data, question=question)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
