"""Hy3 Architecture MCP Server.

A stdio MCP Server that wraps the Hy3 OpenAI-compatible API into a
technical-proposal review workflow:

    fuzzy requirement -> clarification -> proposal -> review -> plan

Four core tools call Hy3 for reasoning; one restricted tool reads local
project files inside a sandboxed workspace root.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
