import asyncio

from hy3_code_review_mcp.server import mcp


def test_server_exposes_three_code_review_tools():
    tools = asyncio.run(mcp.list_tools())
    names = {tool.name for tool in tools}

    assert names == {"review_git_diff", "review_patch", "suggest_tests"}
    assert all(tool.description for tool in tools)
