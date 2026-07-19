"""第二个 MCP 客户端：命令行协议客户端（stdio）。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server.py"
PY = r"D:\Anaconda\python.exe"


def main() -> None:
    env = os.environ.copy()
    env.setdefault("HY3_MCP_ROOT", str(ROOT))
    # Windows 默认管道编码是 gbk，MCP 报文是 utf-8，必须显式指定
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    proc = subprocess.Popen(
        [PY, str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        env=env,
        bufsize=1,
    )
    assert proc.stdin and proc.stdout

    def send(msg: dict) -> None:
        proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        proc.stdin.flush()

    def recv() -> dict:
        while True:
            line = proc.stdout.readline()
            if not line:
                err = proc.stderr.read() if proc.stderr else ""
                raise RuntimeError(f"server closed: {err[:800]}")
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    print("== 客户端: hy3-mcp-check (stdio) ==")
    send(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "hy3-mcp-check", "version": "0.1"},
            },
        }
    )
    init = recv()
    if "result" not in init:
        print("initialize 失败", init)
        sys.exit(1)
    print("initialize: OK")
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = recv()
    names = [t.get("name") for t in tools.get("result", {}).get("tools", [])]
    print("tools (%d):" % len(names), ", ".join(names))

    send(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_dir", "arguments": {"path": "."}},
        }
    )
    call = recv()
    text = ""
    for c in call.get("result", {}).get("content", []):
        if c.get("type") == "text":
            text += c.get("text", "")
    print("-- list_dir --")
    print(text[:500])

    send(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "read_file", "arguments": {"path": "sample.py"}},
        }
    )
    call2 = recv()
    text2 = ""
    for c in call2.get("result", {}).get("content", []):
        if c.get("type") == "text":
            text2 += c.get("text", "")
    print("-- read_file sample.py --")
    print(text2[:300])

    # optional hy3
    if (ROOT / ".env").exists() or os.environ.get("HY3_API_KEY"):
        send(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "hy3_answer",
                    "arguments": {"question": "只回复：ok", "context": ""},
                },
            }
        )
        call3 = recv()
        text3 = ""
        for c in call3.get("result", {}).get("content", []):
            if c.get("type") == "text":
                text3 += c.get("text", "")
        print("-- hy3_answer --")
        print(text3[:400])

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()

    if len(names) >= 3 and "list_dir" in names and "read_file" in names:
        print("\nPASS: 第二个 MCP 客户端调用成功")
        return
    print("\nFAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
