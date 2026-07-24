"""Run a concise MCP Inspector CLI demo against a configured compatible backend."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1]
INSPECTOR = [
    "npm",
    "exec",
    "--yes",
    "--package=@modelcontextprotocol/inspector@0.21.2",
    "--",
    "mcp-inspector",
    "--cli",
    "uv",
    "run",
    "hy3-deep-research",
]


def run_inspector(arguments: list[str], *, timeout: int = 300) -> dict:
    env = os.environ.copy()
    env.setdefault("NO_PROXY", "127.0.0.1,localhost")
    env.setdefault("no_proxy", "127.0.0.1,localhost")
    env.setdefault("NPM_CONFIG_REGISTRY", "https://registry.npmjs.org")
    process = subprocess.run(
        [*INSPECTOR, *arguments],
        cwd=PACKAGE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if process.returncode:
        detail = process.stderr.strip() or process.stdout.strip()
        raise RuntimeError(
            f"Inspector failed with exit code {process.returncode}: {detail}"
        )
    return json.loads(process.stdout)


def clean_report(report: str) -> str:
    if "</think>" in report:
        report = report.rsplit("</think>", 1)[-1]
    lines = [line.rstrip() for line in report.strip().splitlines()]
    return "\n".join(lines[:14])


def main() -> int:
    required = ["HY3_BASE_URL", "HY3_MODEL", "HY3_API_KEY"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    print("Hy3 Deep Research MCP - Inspector CLI smoke test", flush=True)
    print(f"Backend model: {os.environ['HY3_MODEL']}", flush=True)
    print("Transport: stdio", flush=True)
    print(flush=True)

    print("$ mcp-inspector --cli ... --method tools/list", flush=True)
    listed = run_inspector(["--method", "tools/list"])
    names = [tool["name"] for tool in listed["tools"]]
    print(f"Connected. Discovered {len(names)} tools:", flush=True)
    for name in names:
        print(f"  - {name}", flush=True)
    print(flush=True)

    print("$ mcp-inspector --cli ... --method tools/call", flush=True)
    print("  tool: analyze_evidence", flush=True)
    called = run_inspector(
        [
            "--method",
            "tools/call",
            "--tool-name",
            "analyze_evidence",
            "--tool-arg",
            "question=According to the evidence, what context length does Hy3 support?",
            "--tool-arg",
            (
                'sources=[{"title":"Hy3 README excerpt",'
                '"content":"Hy3 supports a context length of 256K."}]'
            ),
            "--tool-arg",
            "focus=Extract the context length and cite the source",
            "--tool-arg",
            "language=English",
        ]
    )
    if called.get("isError"):
        raise RuntimeError(f"MCP tool returned an error: {called}")
    inner = json.loads(called["content"][0]["text"])
    print("Call succeeded (isError=false).", flush=True)
    print("Report:", flush=True)
    print(clean_report(inner["report"]), flush=True)
    print(flush=True)
    print("Sources:", flush=True)
    for source in inner["sources"]:
        print(f"  [{source['id']}] {source['title']}", flush=True)
    print(
        "PASS: MCP client -> stdio server -> compatible API -> MCP result", flush=True
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
