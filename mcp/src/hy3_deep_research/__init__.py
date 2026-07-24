"""Hy3 Deep Research Assistant - an MCP Server powered by Tencent Hunyuan Hy3.

Exposes three MCP tools over stdio transport:
  - search_web     : web search (DuckDuckGo by default, optional Tavily)
  - fetch_url      : extract clean text from a web page
  - deep_research  : multi-step research (decompose -> search -> fetch -> Hy3 synthesis)
"""

from __future__ import annotations

__version__ = "0.1.0"

# Re-export key classes for programmatic use.
from .config import Config, ConfigError, load_config
from .hy3_client import Hy3Client
from .models import (
    FetchResult,
    ResearchCitation,
    ResearchReport,
    SearchResult,
)
from .server import create_server, main

__all__ = [
    "__version__",
    "Config",
    "ConfigError",
    "load_config",
    "Hy3Client",
    "SearchResult",
    "FetchResult",
    "ResearchCitation",
    "ResearchReport",
    "create_server",
    "main",
]
