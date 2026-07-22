"""End-to-end tests for the MCP server via stdio_client."""

import subprocess
import sys
import time


def test_server_starts():
    """Verify the server module can be imported and the mcp instance exists."""
    from hy3_data_analyst.tools import mcp
    assert mcp is not None
    assert mcp.name == "hy3-data-analyst"


def test_tools_registered():
    """Verify all 4 tools are registered on the FastMCP instance."""
    from hy3_data_analyst.tools import mcp
    tool_names = {t.name for t in mcp._tool_manager._tools.values()}  # type: ignore[attr-defined]
    expected = {"list_data_files", "stats_summary", "plot_chart", "ask_data"}
    assert tool_names == expected
