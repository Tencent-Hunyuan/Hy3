"""
Tool Registry — unified management of all tools callable by Hy3.

Architecture (from design doc §5.7):
  Internal tools: git_clone, file_tree, file_read, grep_search,
                  ast_parse, dep_graph_query  → direct Python function calls
  MCP tools:      web_search, code_execution  → via MCP subprocess

Hy3 sees all tools through a uniform JSON Schema interface.
The dispatch layer routes calls to either internal functions or MCP.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

ToolFunc = Callable[..., Coroutine[Any, Any, dict[str, Any]]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolFunc | None = None  # None for MCP tools
    is_mcp: bool = False
    mcp_server_name: str = ""

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI Function Calling JSON Schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Singleton registry for all tools available to Hy3."""

    _instance: ToolRegistry | None = None

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._mcp_process: subprocess.Popen | None = None

    @classmethod
    def get_instance(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Registration ──────────────────────────────────────────

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: ToolFunc,
    ) -> None:
        """Register an internal (direct-call) tool."""
        self._tools[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            is_mcp=False,
        )
        logger.debug("Registered internal tool: %s", name)

    def register_mcp(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        mcp_server_name: str,
    ) -> None:
        """Register an MCP-backed tool (no direct handler)."""
        self._tools[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            is_mcp=True,
            mcp_server_name=mcp_server_name,
        )
        logger.debug("Registered MCP tool: %s → %s", name, mcp_server_name)

    # ── Schema generation ─────────────────────────────────────

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """All tool schemas for passing to Hy3's `tools` parameter."""
        return [t.to_openai_schema() for t in self._tools.values()]

    def get_schemas_for(self, tool_names: list[str]) -> list[dict[str, Any]]:
        """Subset of tool schemas."""
        return [
            t.to_openai_schema()
            for name, t in self._tools.items()
            if name in tool_names
        ]

    # ── Execution dispatch ────────────────────────────────────

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool call and return the result.

        Routes to internal handler or MCP based on tool registration.
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return {"error": f"Unknown tool: {tool_name}"}

        if tool.is_mcp:
            return await self._call_mcp(tool, arguments)

        if tool.handler:
            try:
                result = await tool.handler(**arguments)
                return result
            except Exception as exc:
                logger.exception("Tool %s failed", tool_name)
                return {"error": str(exc)}

        return {"error": f"No handler for tool: {tool_name}"}

    # ── MCP bridge ────────────────────────────────────────────

    async def start_mcp_server(self, command: list[str]) -> None:
        """Launch MCP server as a subprocess (used by web_search + code_exec)."""
        if self._mcp_process is not None:
            logger.warning("MCP server already running")
            return

        self._mcp_process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info("MCP server started: %s", command)

    async def stop_mcp_server(self) -> None:
        """Gracefully terminate MCP server."""
        if self._mcp_process:
            self._mcp_process.terminate()
            try:
                self._mcp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._mcp_process.kill()
            self._mcp_process = None
            logger.info("MCP server stopped")

    async def _call_mcp(self, tool: Tool, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send tool call to MCP server via stdio JSON-RPC."""
        if not self._mcp_process or self._mcp_process.poll() is not None:
            return {"error": "MCP server is not running"}

        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool.name, "arguments": arguments},
            "id": 1,
        }

        try:
            stdin = self._mcp_process.stdin
            stdout = self._mcp_process.stdout
            if stdin is None or stdout is None:
                return {"error": "MCP server pipes unavailable"}

            stdin.write(json.dumps(request) + "\n")
            stdin.flush()
            response_line = stdout.readline()
            if response_line:
                return json.loads(response_line).get("result", {})
            return {"error": "No response from MCP server"}
        except Exception as exc:
            return {"error": f"MCP call failed: {exc}"}
