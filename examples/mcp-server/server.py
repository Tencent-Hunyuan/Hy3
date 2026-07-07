"""Hy3 MCP Server — OpenAI-compatible LLM tools for any MCP client.

Exposes Hy3 (Tencent's 295B MoE model) capabilities as standard MCP tools.
Works with any MCP-compatible client: Claude Code, CodeBuddy, Cursor, Cline, etc.

Architecture::

    MCP Client  ←→  MCP (stdio)  ←→  this server  ←→  Hy3 API (OpenAI-compatible)

Usage::

    pip install -r requirements.txt
    # Configure your MCP client to run: python server.py
    # Set HY3_BASE_URL and HY3_API_KEY environment variables.

Environment variables::

    HY3_BASE_URL  — Hy3 OpenAI-compatible endpoint (default: http://127.0.0.1:8000/v1)
    HY3_API_KEY   — API key (default: "EMPTY" for local vLLM/SGLang deployments)
    HY3_MODEL     — Model name (default: "tencent/Hy3")
"""

from __future__ import annotations

import os
from typing import Any

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
try:
    from openai import OpenAI
except ImportError:
    raise SystemExit("openai is not installed. Run: pip install openai")

try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    raise SystemExit("mcp is not installed. Run: pip install mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("HY3_BASE_URL", "http://127.0.0.1:8000/v1")
API_KEY = os.environ.get("HY3_API_KEY", "EMPTY")
MODEL = os.environ.get("HY3_MODEL", "tencent/Hy3")

_client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
server = Server("hy3")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="hy3_chat",
            description=(
                "Send a message to Hy3 (Tencent's 295B MoE model) and get a "
                "response. Use for general conversation, brainstorming, "
                "explanation, or any text-based task."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message or prompt to send to Hy3.",
                    },
                    "system": {
                        "type": "string",
                        "description": "Optional system prompt to set context/behavior.",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (0.0–2.0, default: 0.7).",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response (default: 2048).",
                    },
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="hy3_code",
            description=(
                "Ask Hy3 to write, explain, review, or debug code. "
                "Hy3 excels at coding tasks including Python, JavaScript, "
                "Go, Rust, and more. Pass a clear description of what "
                "code you need."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Description of the coding task. Be specific about "
                            "language, requirements, and expected output."
                        ),
                    },
                    "language": {
                        "type": "string",
                        "description": "Programming language (python, javascript, go, rust, etc.).",
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (default: 0.3 for code).",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens (default: 4096).",
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="hy3_analyze",
            description=(
                "Analyze text, data, or documents with Hy3. Use for "
                "summarization, sentiment analysis, data extraction, "
                "or structured reasoning tasks."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The text or data to analyze.",
                    },
                    "task": {
                        "type": "string",
                        "description": (
                            "What to do: 'summarize', 'extract', 'classify', "
                            "'sentiment', 'reason', or describe in your own words."
                        ),
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Sampling temperature (default: 0.3).",
                    },
                },
                "required": ["content", "task"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool handler
# ---------------------------------------------------------------------------
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    # ---- hy3_chat -------------------------------------------------------
    if name == "hy3_chat":
        message = arguments.get("message", "")
        if not message or not isinstance(message, str) or not message.strip():
            return [_text("❌ 'message' must be a non-empty string.")]

        messages: list[dict] = []
        system = arguments.get("system")
        if system and isinstance(system, str) and system.strip():
            messages.append({"role": "system", "content": system.strip()})
        messages.append({"role": "user", "content": message.strip()})

        try:
            temperature = float(arguments.get("temperature", 0.7))
            temperature = max(0.0, min(2.0, temperature))
        except (TypeError, ValueError):
            temperature = 0.7

        try:
            max_tokens = int(arguments.get("max_tokens", 2048))
            max_tokens = max(1, min(32768, max_tokens))
        except (TypeError, ValueError):
            max_tokens = 2048

        try:
            resp = _client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return [_text(resp.choices[0].message.content or "(empty response)")]
        except Exception as exc:
            return [_text(f"❌ Hy3 API error: {_safe_err(exc)}")]

    # ---- hy3_code -------------------------------------------------------
    if name == "hy3_code":
        prompt = arguments.get("prompt", "")
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            return [_text("❌ 'prompt' must be a non-empty string.")]

        language = arguments.get("language", "")
        system_msg = (
            f"You are an expert {language} programmer. "
            f"Write clean, well-documented code. Include explanations "
            f"for complex logic. Respond with the code and a brief "
            f"explanation."
            if language
            else "You are an expert programmer. Write clean, well-documented code."
        )

        try:
            temperature = float(arguments.get("temperature", 0.3))
            temperature = max(0.0, min(2.0, temperature))
        except (TypeError, ValueError):
            temperature = 0.3

        try:
            max_tokens = int(arguments.get("max_tokens", 4096))
            max_tokens = max(1, min(32768, max_tokens))
        except (TypeError, ValueError):
            max_tokens = 4096

        try:
            resp = _client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt.strip()},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return [_text(resp.choices[0].message.content or "(empty response)")]
        except Exception as exc:
            return [_text(f"❌ Hy3 API error: {_safe_err(exc)}")]

    # ---- hy3_analyze ----------------------------------------------------
    if name == "hy3_analyze":
        content = arguments.get("content", "")
        task = arguments.get("task", "")
        if not content or not isinstance(content, str) or not content.strip():
            return [_text("❌ 'content' must be a non-empty string.")]
        if not task or not isinstance(task, str) or not task.strip():
            return [_text("❌ 'task' must be a non-empty string.")]

        task_lower = task.strip().lower()
        task_prompts = {
            "summarize": "Summarize the following content concisely:",
            "extract": "Extract key information and structured data from:",
            "classify": "Classify the following content into categories:",
            "sentiment": "Analyze the sentiment and emotional tone of:",
            "reason": "Step-by-step reasoning analysis of:",
        }
        instruction = task_prompts.get(task_lower, task.strip())

        try:
            temperature = float(arguments.get("temperature", 0.3))
            temperature = max(0.0, min(2.0, temperature))
        except (TypeError, ValueError):
            temperature = 0.3

        try:
            resp = _client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": "You are a precise analyst. Be concise and accurate."},
                    {"role": "user", "content": f"{instruction}\n\n{content.strip()}"},
                ],
                temperature=temperature,
                max_tokens=4096,
            )
            return [_text(resp.choices[0].message.content or "(empty response)")]
        except Exception as exc:
            return [_text(f"❌ Hy3 API error: {_safe_err(exc)}")]

    return [_text(f"❌ Unknown tool: {name!r}")]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _text(content: str) -> TextContent:
    return TextContent(type="text", text=content)


def _safe_err(exc: BaseException) -> str:
    msg = str(exc).strip()
    if len(msg) > 300:
        msg = msg[:300] + "..."
    return msg


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )


def main() -> None:
    import asyncio
    asyncio.run(_main())


if __name__ == "__main__":
    main()
