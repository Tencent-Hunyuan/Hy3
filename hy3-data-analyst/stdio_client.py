#!/usr/bin/env python3
"""Simple MCP stdio test client for protocol verification.

Usage:
    python stdio_client.py

This launches the hy3-data-analyst server as a subprocess, sends an
initialize + tools/list request, and prints the response. No GUI or real
Hy3 API key is required.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def send_rpc(proc: subprocess.Popen, request: dict) -> dict:
    """Send a JSON-RPC request to the server and return the response."""
    payload = json.dumps(request) + "\n"
    proc.stdin.write(payload)
    proc.stdin.flush()
    line = proc.stdout.readline()
    return json.loads(line)


def main() -> None:
    python = sys.executable
    server_module = "hy3_data_analyst.server"

    print(f"Launching server: {python} -m {server_module}")
    proc = subprocess.Popen(
        [python, "-m", server_module],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    try:
        # Step 1: Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "stdio-test-client", "version": "0.1.0"},
            },
        }
        print("\n>>> initialize")
        resp = send_rpc(proc, init_req)
        print(f"<<< {json.dumps(resp, indent=2, ensure_ascii=False)[:500]}")

        # Send initialized notification
        notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        proc.stdin.write(json.dumps(notif) + "\n")
        proc.stdin.flush()

        # Step 2: List tools
        list_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        print("\n>>> tools/list")
        resp = send_rpc(proc, list_req)
        tools = resp.get("result", {}).get("tools", [])
        print(f"<<< Found {len(tools)} tool(s):")
        for t in tools:
            print(f"    - {t['name']}: {t['description'][:80]}...")

        # Step 3: Call list_data_files (doesn't need API key)
        call_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_data_files", "arguments": {"path": "."}},
        }
        print("\n>>> tools/call list_data_files")
        resp = send_rpc(proc, call_req)
        content = resp.get("result", {}).get("content", [{}])
        text = content[0].get("text", "") if content else str(resp)
        print(f"<<< {text[:300]}")

        print("\nAll tests passed!")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
