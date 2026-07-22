"""MCP Server entry point. Run with: hy3-data-analyst or python -m hy3_data_analyst.server"""

from .tools import mcp


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
