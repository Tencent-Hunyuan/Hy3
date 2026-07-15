from typing import Annotated

from mcp.server.fastmcp import FastMCP

from hy3_mcp_server.tools.ask import ask_hy3
from hy3_mcp_server.tools.file_analyze import file_analyze
from hy3_mcp_server.tools.search import search_and_analyze

mcp = FastMCP("hy3-mcp-server")


@mcp.tool(
    name="ask_hy3",
    description="Directly chat with Hy3 AI model. Supports reasoning modes: no_think (fast), low (brief reasoning), high (deep chain-of-thought).",
)
async def ask_hy3_tool(
    prompt: str,
    reasoning_effort: str = "no_think",
) -> str:
    return await ask_hy3(prompt, reasoning_effort)


@mcp.tool(
    name="search_and_analyze",
    description="Search the web for a topic and use Hy3 to analyze the results into a comprehensive answer. Combines DuckDuckGo search with Hy3 reasoning.",
)
async def search_and_analyze_tool(
    query: str,
    max_results: int = 5,
) -> str:
    return await search_and_analyze(query, max_results)


@mcp.tool(
    name="file_analyze",
    description="Read a local file and ask Hy3 to analyze, summarize, or answer questions about its content. Supports text files up to ~50K characters.",
)
async def file_analyze_tool(
    file_path: str,
    prompt: str,
) -> str:
    return await file_analyze(file_path, prompt)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
