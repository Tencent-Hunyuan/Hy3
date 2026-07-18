"""通过官方 MCP 客户端验证真实 stdio 子进程。"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SMOKE_ROOT = Path(__file__).resolve().parent / "fixtures" / "smoke"
EXPECTED_TOOLS = {
    "hy3_kb_ask",
    "hy3_kb_index_documents",
    "hy3_kb_list_sources",
    "hy3_kb_search",
    "hy3_kb_summarize_source",
}
KEY_PREFIXES = ("sk-", "sk-or-v1-", "Bearer ")
SMOKE_SCRIPT = PACKAGE_ROOT / "scripts" / "stdio_smoke.py"
FAKE_SERVER = Path(__file__).resolve().parent / "fixtures" / "fake_stdio_server.py"


def _offline_environment(storage_dir: Path) -> dict[str, str]:
    """继承启动所需环境, 但显式移除所有远端 API 密钥。"""
    child_env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in {"HY3_API_KEY", "OPENROUTER_API_KEY", "PYTHON_DOTENV_DISABLED"}
    }
    child_env.update(
        {
            "PYTHONUTF8": "1",
            "HY3_KB_ROOTS": os.fspath(SMOKE_ROOT),
            "HY3_KB_STORAGE_DIR": os.fspath(storage_dir),
        }
    )
    return child_env


def _environment_with_fake_keys(storage_dir: Path) -> dict[str, str]:
    """为 CLI 进程注入测试密钥, 证明脚本会在启动 server 前移除。"""
    environment = _offline_environment(storage_dir)
    environment.update(
        {
            "HY3_API_KEY": "sk-stdio-test-secret",
            "OPENROUTER_API_KEY": "sk-or-v1-stdio-test-secret",
        }
    )
    return environment


def _smoke_command(
    tmp_path: Path,
    *,
    optimized: bool = False,
    command_path: str | None = None,
    server_args: list[str] | None = None,
    timeout_seconds: float | None = None,
) -> list[str]:
    """构造真实 smoke 客户端命令。"""
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.extend(
        [
            os.fspath(SMOKE_SCRIPT),
            "--command",
            command_path or sys.executable,
        ]
    )
    for server_arg in server_args or ["-m", "hy3_knowledge_mcp"]:
        command.append(f"--server-arg={server_arg}")
    command.extend(
        [
            "--knowledge-root",
            os.fspath(SMOKE_ROOT),
            "--storage-dir",
            os.fspath(tmp_path / "storage"),
        ]
    )
    if timeout_seconds is not None:
        command.extend(["--timeout-seconds", str(timeout_seconds)])
    return command


def _process_exists(pid: int) -> bool:
    """跨平台判断测试子进程是否仍存在。"""
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@pytest.mark.anyio
async def test_real_stdio_process_is_protocol_clean_and_offline(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """真实子进程的 stdout 仅含 JSON-RPC, 且离线工具不需要密钥。"""
    monkeypatch.setenv("HY3_API_KEY", "sk-stdio-test-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-stdio-test-secret")
    assert (SMOKE_ROOT / "guide.md").is_file()
    stderr_path = tmp_path / "server.stderr.log"
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "hy3_knowledge_mcp"],
        cwd=PACKAGE_ROOT,
        env=_offline_environment(tmp_path / "storage"),
        encoding="utf-8",
        encoding_error_handler="strict",
    )

    caplog.clear()
    with stderr_path.open("w+", encoding="utf-8") as errlog:
        with caplog.at_level(logging.ERROR, logger="mcp.client.stdio"):
            with anyio.fail_after(20):
                async with stdio_client(server, errlog=errlog) as (read, write):
                    async with ClientSession(
                        read,
                        write,
                        read_timeout_seconds=timedelta(seconds=10),
                    ) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        assert {tool.name for tool in tools.tools} == EXPECTED_TOOLS

                        indexed = await session.call_tool(
                            "hy3_kb_index_documents",
                            arguments={
                                "collection": "smoke",
                                "path": os.fspath(SMOKE_ROOT),
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
                        assert indexed.isError is False
                        assert listed.isError is False
                        assert searched.isError is False

        errlog.seek(0)
        server_stderr = errlog.read()

    parse_errors = [
        record
        for record in caplog.records
        if record.name == "mcp.client.stdio"
        and "Failed to parse JSONRPC message from server" in record.getMessage()
    ]
    assert parse_errors == []
    assert not any(prefix in server_stderr for prefix in KEY_PREFIXES)


def test_stdio_smoke_cli_prints_only_client_success(tmp_path: Path) -> None:
    """成功 smoke 只允许客户端在 stdout 打印固定成功标记。"""
    result = subprocess.run(
        _smoke_command(tmp_path),
        cwd=PACKAGE_ROOT,
        env=_environment_with_fake_keys(tmp_path / "outer-storage"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "STDIO SMOKE OK\n"
    assert not any(prefix in result.stderr for prefix in KEY_PREFIXES)


def test_stdio_smoke_cli_returns_one_on_failure(tmp_path: Path) -> None:
    """任何协议或断言失败都必须返回 1, 不能误报成功。"""
    result = subprocess.run(
        _smoke_command(tmp_path, command_path=os.fspath(tmp_path / "missing-command.exe")),
        cwd=PACKAGE_ROOT,
        env=_environment_with_fake_keys(tmp_path / "outer-storage"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
        check=False,
    )

    assert result.returncode == 1
    assert "STDIO SMOKE OK" not in result.stdout
    assert not any(prefix in result.stderr for prefix in KEY_PREFIXES)


@pytest.mark.parametrize("optimized", [False, True])
def test_stdio_smoke_rejects_removed_secret_from_server_stderr(
    tmp_path: Path,
    optimized: bool,
) -> None:
    """普通与优化模式都必须扫描 server stderr 中的完整父环境 secret。"""
    parent_secret = "parent-secret-4f2dd917"
    environment = _offline_environment(tmp_path / "outer-storage")
    environment.update(
        {
            "hy3_api_key": parent_secret,
            "FAKE_STDERR_SENTINEL": parent_secret,
        }
    )
    result = subprocess.run(
        _smoke_command(
            tmp_path,
            optimized=optimized,
            server_args=[os.fspath(FAKE_SERVER)],
        ),
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
        check=False,
    )

    assert result.returncode == 1
    assert "STDIO SMOKE OK" not in result.stdout
    assert parent_secret not in result.stderr


def test_stdio_smoke_disables_cwd_dotenv_loading(tmp_path: Path) -> None:
    """smoke 启动的 server 不得从当前目录 .env 读取密钥。"""
    dotenv_secret = "dotenv-secret-c44b399e"
    (tmp_path / ".env").write_text(f"HY3_API_KEY={dotenv_secret}\n", encoding="utf-8")
    environment = _offline_environment(tmp_path / "outer-storage")
    environment["FAKE_FAIL_ON_DOTENV"] = "1"
    result = subprocess.run(
        _smoke_command(tmp_path, server_args=[os.fspath(FAKE_SERVER)]),
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "STDIO SMOKE OK\n"
    assert dotenv_secret not in result.stderr


def test_stdio_smoke_protocol_failure_keeps_secret_out_of_client_error(tmp_path: Path) -> None:
    """协议失败时仍扫描 stderr, 且客户端错误不得拼接 server secret。"""
    parent_secret = "protocol-secret-931fb23a"
    environment = _offline_environment(tmp_path / "outer-storage")
    environment.update(
        {
            "HY3_API_KEY": parent_secret,
            "FAKE_STDERR_SENTINEL": parent_secret,
            "FAKE_STDIO_MODE": "invalid",
        }
    )
    result = subprocess.run(
        _smoke_command(tmp_path, server_args=[os.fspath(FAKE_SERVER)]),
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
        check=False,
    )

    assert result.returncode == 1
    assert "STDIO SMOKE OK" not in result.stdout
    assert parent_secret not in result.stderr


def test_stdio_smoke_timeout_terminates_hanging_server(tmp_path: Path) -> None:
    """客户端超时返回 1 后不得遗留挂起 server 子进程。"""
    pid_file = tmp_path / "server.pid"
    environment = _offline_environment(tmp_path / "outer-storage")
    environment.update(
        {
            "FAKE_STDIO_MODE": "hang",
            "FAKE_PID_FILE": os.fspath(pid_file),
        }
    )
    result = subprocess.run(
        _smoke_command(
            tmp_path,
            server_args=[os.fspath(FAKE_SERVER)],
            timeout_seconds=1,
        ),
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=10,
        check=False,
    )

    assert result.returncode == 1
    assert "STDIO SMOKE OK" not in result.stdout
    pid = int(pid_file.read_text(encoding="utf-8"))
    deadline = time.monotonic() + 3
    while _process_exists(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not _process_exists(pid)
