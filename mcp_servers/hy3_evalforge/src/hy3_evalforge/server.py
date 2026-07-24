"""The local stdio-only FastMCP server."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from hy3_evalforge.tools import compare_runs, design_spec, generate_cases, score_run


def create_server() -> FastMCP:
    """Create a server with the four stable EvalForge tool names and schemas."""
    server = FastMCP(
        "Hy3 EvalForge",
        instructions=(
            "Evaluate existing AI-system JSONL outputs with deterministic rules and Hy3. "
            "This local server never runs the target system or exposes an HTTP transport."
        ),
        log_level="ERROR",
    )
    for module in (design_spec, generate_cases, score_run, compare_runs):
        module.register(server)
    return server


mcp = create_server()


def main() -> None:
    """Run exactly one stdio transport; do not write application logs to stdout."""
    mcp.run(transport="stdio")
