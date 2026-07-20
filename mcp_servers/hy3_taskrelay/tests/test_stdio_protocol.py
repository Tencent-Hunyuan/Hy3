import json
import os
import subprocess
import sys
from pathlib import Path


def test_raw_stdio_is_json_only_and_exits_cleanly() -> None:
    package_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(package_root / "src")
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "taskrelay-test", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "taskrelay_unknown", "arguments": {}},
        },
    ]
    process = subprocess.Popen(
        [sys.executable, "-m", "hy3_taskrelay"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environment,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    responses = []
    try:
        process.stdin.write(json.dumps(messages[0], separators=(",", ":")) + "\n")
        process.stdin.flush()
        responses.append(json.loads(process.stdout.readline()))

        for message in messages[1:3]:
            process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        process.stdin.flush()
        responses.append(json.loads(process.stdout.readline()))

        process.stdin.write(json.dumps(messages[3], separators=(",", ":")) + "\n")
        process.stdin.flush()
        responses.append(json.loads(process.stdout.readline()))
        process.stdin.close()
        return_code = process.wait(timeout=20)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    assert return_code == 0
    assert [response["id"] for response in responses] == [1, 2, 3]
    assert responses[2]["result"]["isError"] is True
