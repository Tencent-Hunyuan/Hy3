"""为 stdio smoke 回归测试提供可控子进程行为。"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


def _write_stderr_sentinel() -> None:
    """按测试要求向 server stderr 写入内存 sentinel。"""
    sentinel = os.environ.get("FAKE_STDERR_SENTINEL")
    if sentinel:
        print(sentinel, file=sys.stderr, flush=True)


def _run_tool_error_server() -> None:
    """暴露精确工具集, 并让 index 返回工具错误。"""
    from mcp.server.fastmcp import FastMCP
    from mcp.server.fastmcp.exceptions import ToolError

    mcp = FastMCP("fake_tool_error")

    @mcp.tool(name="hy3_kb_index_documents")
    def index_documents(collection: str, path: str) -> str:
        del collection, path
        raise ToolError("forced tool failure")

    @mcp.tool(name="hy3_kb_list_sources")
    def list_sources(collection: str) -> str:
        return collection

    @mcp.tool(name="hy3_kb_search")
    def search(collection: str, query: str, limit: int = 3) -> str:
        return f"{collection}:{query}:{limit}"

    @mcp.tool(name="hy3_kb_ask")
    def ask(collection: str, question: str) -> str:
        return f"{collection}:{question}"

    @mcp.tool(name="hy3_kb_summarize_source")
    def summarize(collection: str, source_path: str) -> str:
        return f"{collection}:{source_path}"

    mcp.run(transport="stdio")


def main() -> None:
    """根据环境变量选择真实、协议失败或挂起模式。"""
    mode = os.environ.get("FAKE_STDIO_MODE", "real")
    _write_stderr_sentinel()

    if mode == "invalid":
        print("not-json-rpc", flush=True)
        raise SystemExit(2)

    if mode == "hang":
        pid_file = Path(os.environ["FAKE_PID_FILE"])
        pid_file.write_text(str(os.getpid()), encoding="utf-8")
        time.sleep(60)
        return

    if mode == "tool_error":
        _run_tool_error_server()
        return

    load_dotenv(Path.cwd() / ".env", override=False)
    dotenv_secret = os.environ.get("HY3_API_KEY")
    if dotenv_secret and os.environ.get("FAKE_FAIL_ON_DOTENV") == "1":
        print(dotenv_secret, file=sys.stderr, flush=True)
        raise SystemExit(3)

    from hy3_knowledge_mcp.server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
