"""第二个 MCP 客户端：命令行 stdio 协议测试。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "server.py"
PY = sys.executable


def main() -> None:
    env = os.environ.copy()
    env.setdefault("HY3_MCP_ROOT", str(ROOT))
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

    print("== 客户端: hy3-mcp-data-analysis-check (stdio) ==")

    # Initialize
    send({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "hy3-mcp-check", "version": "0.1"},
        },
    })
    init = recv()
    if "result" not in init:
        print("initialize 失败", json.dumps(init, ensure_ascii=False)[:500])
        sys.exit(1)
    print("initialize: OK")
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # List tools
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools_resp = recv()
    tools = tools_resp.get("result", {}).get("tools", [])
    names = [t.get("name") for t in tools]
    print(f"tools ({len(names)}):", ", ".join(names))

    expected_tools = {"load_dataset", "web_search", "hy3_analyze", "hy3_chart_guide"}
    found = set(names)
    if not expected_tools.issubset(found):
        print(f"FAIL: 缺少 tool: {expected_tools - found}")
        proc.terminate()
        sys.exit(1)

    # Call load_dataset
    send({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "load_dataset", "arguments": {"path": "sample_data.csv", "max_rows": 5}},
    })
    call1 = recv()
    text1 = ""
    for c in call1.get("result", {}).get("content", []):
        if c.get("type") == "text":
            text1 += c.get("text", "")
    print("-- load_dataset --")
    print(text1[:500])

    if "product" not in text1 or "总行数" not in text1:
        print("FAIL: load_dataset 输出不完整")
        proc.terminate()
        sys.exit(1)

    # Call web_search
    send({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "web_search", "arguments": {"query": "Python pandas", "max_results": 2}},
    })
    call2 = recv()
    text2 = ""
    for c in call2.get("result", {}).get("content", []):
        if c.get("type") == "text":
            text2 += c.get("text", "")
    print("-- web_search --")
    print(text2[:500])

    if "搜索源:" not in text2:
        print("FAIL: web_search 输出格式错误")
        proc.terminate()
        sys.exit(1)

    # Call hy3_* if API key is set
    if (ROOT / ".env").exists() or os.environ.get("HY3_API_KEY"):
        send({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "hy3_analyze",
                "arguments": {"dataset_path": "sample_data.csv", "question": "哪个区域销售额最高？简短回答", "include_web": False},
            },
        })
        call3 = recv()
        text3 = ""
        for c in call3.get("result", {}).get("content", []):
            if c.get("type") == "text":
                text3 += c.get("text", "")
        print("-- hy3_analyze --")
        print(text3[:400])

        send({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "hy3_chart_guide",
                "arguments": {"dataset_path": "sample_data.csv", "goal": "柱状图对比区域销售额"},
            },
        })
        call4 = recv()
        text4 = ""
        for c in call4.get("result", {}).get("content", []):
            if c.get("type") == "text":
                text4 += c.get("text", "")
        print("-- hy3_chart_guide --")
        print(text4[:400])

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()

    print("\nPASS: MCP 协议端到端测试通过")
    return


if __name__ == "__main__":
    main()
