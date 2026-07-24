"""FastMCP server assembly and entry point.

Run with `hy3-deep-research` (console script) or `python -m hy3_deep_research`.
Uses stdio transport by default, which is what local MCP clients expect.
"""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP

from .config import ConfigError, load_config
from .hy3_client import Hy3Client
from .tools import (
    register_fetch_tools,
    register_research_tools,
    register_search_tools,
)

logger = logging.getLogger("hy3_deep_research")


def _setup_logging() -> None:
    """Configure logging to stderr (stdout is reserved for MCP protocol)."""
    level = os.environ.get("HY3_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="[%(name)s] %(levelname)s: %(message)s",
        stream=__import__("sys").stderr,
    )


def create_server() -> FastMCP:
    """Build and return the configured FastMCP server instance."""
    _setup_logging()
    config = load_config()
    hy3 = Hy3Client(config)
    logger.info("Server starting (model=%s, base_url=%s)", config.hunyuan_model, config.hunyuan_base_url)

    mcp = FastMCP(
        "Hy3 Deep Research Assistant",
        instructions=(
            "This MCP server provides deep research capabilities powered by "
            "Tencent Hunyuan Hy3. Available tools:\n"
            "- search_web: search the web for information (DuckDuckGo, no key needed).\n"
            "- fetch_url: extract the clean main text of a web page.\n"
            "- deep_research: run a full multi-step research (decompose -> search -> "
            "read -> Hy3 synthesis) and return a report with inline citations.\n"
            "All API keys are read from environment variables; none are hardcoded."
        ),
    )

    register_search_tools(mcp, config)
    register_fetch_tools(mcp, config)
    register_research_tools(mcp, config, hy3)

    logger.info("Registered 3 tools: search_web, fetch_url, deep_research")
    return mcp


def main() -> None:
    """Entry point for the console script / `python -m hy3_deep_research`."""
    try:
        mcp = create_server()
    except ConfigError as exc:
        # Print to stderr so the MCP client surfaces a readable error.
        import sys

        print(f"[hy3-deep-research] configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2)
    mcp.run()


if __name__ == "__main__":
    main()
