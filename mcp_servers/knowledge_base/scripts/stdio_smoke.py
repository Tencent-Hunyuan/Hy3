"""使用官方 MCP SDK 对真实 stdio server 执行离线 smoke。"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "hy3_kb_ask",
    "hy3_kb_index_documents",
    "hy3_kb_list_sources",
    "hy3_kb_search",
    "hy3_kb_summarize_source",
}
KEY_PREFIXES = ("sk-", "sk-or-v1-", "Bearer ")
SECRET_ENV_NAMES = {"HY3_API_KEY", "OPENROUTER_API_KEY"}


class SmokeFailure(RuntimeError):
    """表示不包含 server 原始输出的安全 smoke 失败。"""


def _require(condition: bool, message: str) -> None:
    """显式校验 smoke 条件, 在 python -O 下仍然生效。"""
    if not condition:
        raise SmokeFailure(message)


class _ProtocolErrorHandler(logging.Handler):
    """记录 MCP 客户端发现的非 JSON-RPC stdout。"""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.parse_errors: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "Failed to parse JSONRPC message from server" in message:
            self.parse_errors.append(message)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """解析 smoke 子进程与离线目录参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", default=sys.executable)
    parser.add_argument("--server-arg", action="append", default=[])
    parser.add_argument("--knowledge-root", type=Path, required=True)
    parser.add_argument("--storage-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    return parser.parse_args(argv)


def _offline_environment(
    knowledge_root: Path,
    storage_dir: Path,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """保留 Python/uvx 启动环境, 并移除所有远端 API 密钥。"""
    removed_secrets = tuple(
        value for key, value in os.environ.items() if key.upper() in SECRET_ENV_NAMES and value
    )
    child_env = {
        key: value for key, value in os.environ.items() if key.upper() not in SECRET_ENV_NAMES
    }
    child_env.update(
        {
            "PYTHONUTF8": "1",
            "PYTHON_DOTENV_DISABLED": "1",
            "HY3_KB_ROOTS": os.fspath(knowledge_root.resolve()),
            "HY3_KB_STORAGE_DIR": os.fspath(storage_dir.resolve()),
        }
    )
    return child_env, removed_secrets


def _stderr_contains_secret(server_stderr: str, removed_secrets: tuple[str, ...]) -> bool:
    """检测完整父环境 secret 和常见大小写不敏感 key 前缀。"""
    if any(secret in server_stderr for secret in removed_secrets):
        return True
    folded_stderr = server_stderr.casefold()
    return any(prefix.casefold() in folded_stderr for prefix in KEY_PREFIXES)


async def _run_smoke(options: argparse.Namespace) -> None:
    """连接 server 并验证 initialize、工具清单和三个离线工具。"""
    knowledge_root = options.knowledge_root.resolve()
    storage_dir = options.storage_dir.resolve()
    _require(knowledge_root.is_dir(), "knowledge root does not exist")
    _require(options.timeout_seconds > 0, "timeout seconds must be positive")

    child_env, removed_secrets = _offline_environment(knowledge_root, storage_dir)

    protocol_errors = _ProtocolErrorHandler()
    client_logger = logging.getLogger("mcp.client.stdio")
    client_logger.addHandler(protocol_errors)
    try:
        with tempfile.TemporaryDirectory(prefix="hy3-stdio-smoke-") as temp_dir:
            stderr_path = Path(temp_dir) / "server.stderr.log"
            operation_failed = False
            server = StdioServerParameters(
                command=options.command,
                args=options.server_arg or ["-m", "hy3_knowledge_mcp"],
                cwd=Path.cwd(),
                env=child_env,
                encoding="utf-8",
                encoding_error_handler="strict",
            )
            try:
                with stderr_path.open("w", encoding="utf-8") as errlog:
                    with anyio.fail_after(options.timeout_seconds):
                        async with stdio_client(server, errlog=errlog) as (read, write):
                            async with ClientSession(
                                read,
                                write,
                                read_timeout_seconds=timedelta(seconds=15),
                            ) as session:
                                await session.initialize()
                                tools = await session.list_tools()
                                _require(
                                    {tool.name for tool in tools.tools} == EXPECTED_TOOLS,
                                    "server exposed an unexpected tool set",
                                )

                                indexed = await session.call_tool(
                                    "hy3_kb_index_documents",
                                    arguments={
                                        "collection": "smoke",
                                        "path": os.fspath(knowledge_root),
                                    },
                                )
                                listed = await session.call_tool(
                                    "hy3_kb_list_sources",
                                    arguments={"collection": "smoke"},
                                )
                                searched = await session.call_tool(
                                    "hy3_kb_search",
                                    arguments={
                                        "collection": "smoke",
                                        "query": "Hy3",
                                        "limit": 3,
                                    },
                                )
                                _require(indexed.isError is False, "index tool failed")
                                _require(listed.isError is False, "list tool failed")
                                _require(searched.isError is False, "search tool failed")
            except BaseException:
                operation_failed = True

            server_stderr = stderr_path.read_text(encoding="utf-8")
            _require(
                not _stderr_contains_secret(server_stderr, removed_secrets),
                "server stderr contained secret material",
            )
            _require(protocol_errors.parse_errors == [], "server stdout was not valid JSON-RPC")
            _require(not operation_failed, "stdio protocol operation failed")
    finally:
        client_logger.removeHandler(protocol_errors)


def main(argv: list[str] | None = None) -> int:
    """运行 smoke; 失败时仅写 stderr 并返回 1。"""
    try:
        anyio.run(_run_smoke, _parse_args(argv))
    except SmokeFailure as exc:
        print(f"STDIO SMOKE FAILED: {exc}", file=sys.stderr)
        return 1
    except BaseException:
        print("STDIO SMOKE FAILED: unexpected client error", file=sys.stderr)
        return 1
    print("STDIO SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
