"""Perform an initialize and tools/list handshake with an installed stdio command."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def _send(process: subprocess.Popen[str], message: dict[str, object]) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def _receive(process: subprocess.Popen[str]) -> dict[str, object]:
    assert process.stdout is not None
    line = process.stdout.readline()
    if not line:
        raise RuntimeError("stdio server exited before returning a JSON-RPC response")
    return json.loads(line)


def run(command: Path) -> dict[str, object]:
    process = subprocess.Popen(
        [str(command)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "taskrelay-smoke", "version": "1.0"},
                },
            },
        )
        initialized = _receive(process)
        _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        _send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_response = _receive(process)
        assert process.stdin is not None
        process.stdin.close()
        return_code = process.wait(timeout=20)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
    if return_code != 0:
        raise RuntimeError(f"stdio server exited with code {return_code}")
    tool_names = [tool["name"] for tool in tools_response["result"]["tools"]]
    return {
        "protocol_version": initialized["result"]["protocolVersion"],
        "tool_names": tool_names,
        "return_code": return_code,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", type=Path)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.command), indent=2))


if __name__ == "__main__":
    main()
