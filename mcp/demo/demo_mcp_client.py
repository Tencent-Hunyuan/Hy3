#!/usr/bin/env python3
"""Demo script: call the Hy3 Deep Research MCP Server via the MCP protocol.

This script spawns the MCP server as a subprocess, performs the MCP
handshake, lists tools, and calls each one in sequence. It demonstrates
exactly what an MCP client (Cursor, Cline, etc.) would do.

Prerequisites:
    - HUNYUAN_API_KEY environment variable must be set.
    - The package must be installed: pip install -e ".[dev]"
      (or set PYTHONPATH to src/)

Usage:
    # Set your key first
    export HUNYUAN_API_KEY=sk-your-key-here

    # Run the demo
    python demo/demo_mcp_client.py

    # Or specify a different query
    python demo/demo_mcp_client.py --query "What is Mixture of Experts in LLMs?"
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

# --- MCP protocol helpers -------------------------------------------------

_NEXT_ID = 1


def _next_id() -> int:
    global _NEXT_ID
    cid = _NEXT_ID
    _NEXT_ID += 1
    return cid


def _send(proc: subprocess.Popen, msg: dict) -> None:
    """Send a single JSON-RPC message (newline-delimited)."""
    line = json.dumps(msg) + "\n"
    data = line.encode("utf-8")
    assert proc.stdin is not None
    proc.stdin.write(data)
    proc.stdin.flush()


def _recv(proc: subprocess.Popen, expected_id: int, timeout: float = 300) -> dict:
    """Read lines until we get the response for *expected_id*."""
    assert proc.stdout is not None
    deadline = time.time() + timeout
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == expected_id:
            return msg
    raise TimeoutError(f"timed out waiting for response id={expected_id}")


def call_tool(proc: subprocess.Popen, name: str, arguments: dict) -> dict:
    """Call an MCP tool and return the parsed result."""
    cid = _next_id()
    _send(proc, {
        "jsonrpc": "2.0",
        "id": cid,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    })
    resp = _recv(proc, cid)
    if "error" in resp:
        return {"error": resp["error"]}
    result = resp.get("result", {})
    # MCP wraps text content in a list of content blocks.
    content_blocks = result.get("content", [])
    texts = []
    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(block["text"])
    raw_text = "\n".join(texts) if texts else json.dumps(result)
    # Try to parse as JSON; fall back to raw text.
    try:
        return json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return {"raw": raw_text}


# --- Pretty printer -------------------------------------------------------

def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# --- Main demo flow -------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demo client for the Hy3 Deep Research MCP Server"
    )
    parser.add_argument(
        "--query",
        default="What are the key architectural innovations in Tencent Hunyuan Hy3?",
        help="Research question for the deep_research tool",
    )
    parser.add_argument(
        "--server-cmd",
        default=None,
        help="Command to start the MCP server (default: python -m hy3_deep_research)",
    )
    args = parser.parse_args()

    if not os.environ.get("HUNYUAN_API_KEY"):
        print("ERROR: HUNYUAN_API_KEY is not set.", file=sys.stderr)
        print("  export HUNYUAN_API_KEY=sk-your-key-here", file=sys.stderr)
        sys.exit(1)

    # --- Start the MCP server as a subprocess -----------------------------
    cmd = args.server_cmd or [sys.executable, "-m", "hy3_deep_research"]
    if isinstance(cmd, str):
        cmd = cmd.split()

    _print_section("Starting MCP Server")
    print(f"Command: {' '.join(cmd)}")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # --- Step 1: MCP handshake (initialize) ---------------------------
        _print_section("Step 1: MCP Initialize")
        init_id = _next_id()
        _send(proc, {
            "jsonrpc": "2.0",
            "id": init_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "demo-client", "version": "0.1.0"},
            },
        })
        init_resp = _recv(proc, init_id)
        server_info = init_resp.get("result", {}).get("serverInfo", {})
        print(f"Server: {server_info.get('name', '?')} v{server_info.get('version', '?')}")

        # Send initialized notification (no response expected)
        _send(proc, {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        })

        # --- Step 2: List tools ------------------------------------------
        _print_section("Step 2: List Tools")
        list_id = _next_id()
        _send(proc, {
            "jsonrpc": "2.0",
            "id": list_id,
            "method": "tools/list",
            "params": {},
        })
        list_resp = _recv(proc, list_id)
        tools = list_resp.get("result", {}).get("tools", [])
        for t in tools:
            print(f"  - {t['name']}: {t.get('description', '')[:80]}...")

        # --- Step 3: Call search_web -------------------------------------
        _print_section("Step 3: Call search_web")
        search_result = call_tool(proc, "search_web", {
            "query": "Tencent Hunyuan Hy3 model",
            "max_results": 3,
        })
        if "error" in search_result:
            print(f"  Error: {search_result['error']}")
        else:
            results = search_result if isinstance(search_result, list) else [search_result]
            for i, r in enumerate(results, 1):
                if "error" in r:
                    print(f"  [{i}] Error: {r['error']}")
                else:
                    print(f"  [{i}] {r.get('title', '?')}")
                    print(f"      URL: {r.get('url', '?')}")

        # --- Step 4: Call fetch_url (if we got a search result) -----------
        first_url = None
        if isinstance(search_result, list):
            for r in search_result:
                if isinstance(r, dict) and r.get("url"):
                    first_url = r["url"]
                    break

        if first_url:
            _print_section("Step 4: Call fetch_url")
            print(f"  URL: {first_url}")
            fetch_result = call_tool(proc, "fetch_url", {
                "url": first_url,
                "max_chars": 2000,
            })
            if fetch_result.get("success"):
                print(f"  Title: {fetch_result.get('title', '?')}")
                content = fetch_result.get("content", "")
                print(f"  Content (first 300 chars): {content[:300]}...")
            else:
                print(f"  Error: {fetch_result.get('error', 'unknown')}")
        else:
            _print_section("Step 4: Call fetch_url (skipped — no URL from search)")

        # --- Step 5: Call deep_research ----------------------------------
        _print_section("Step 5: Call deep_research")
        print(f"  Query: {args.query}")
        print("  (this may take 30-60 seconds...)")
        research_result = call_tool(proc, "deep_research", {
            "query": args.query,
            "max_search_results": 3,
            "max_sources_to_fetch": 2,
            "reasoning_effort": "high",
        })

        _print_section("Deep Research Result")
        print(f"  Sub-queries: {research_result.get('sub_queries', [])}")
        print(f"  Sources searched: {research_result.get('sources_searched', 0)}")
        print(f"  Sources fetched: {research_result.get('sources_fetched', 0)}")
        print(f"\n  Report:\n{research_result.get('report', '(empty)')}")
        print(f"\n  Citations:")
        for c in research_result.get("citations", []):
            print(f"    [{c.get('index', '?')}] {c.get('title', '?')} - {c.get('url', '?')}")

        _print_section("Demo Complete!")

    except Exception as exc:
        print(f"\nDemo failed: {exc}", file=sys.stderr)
        # Print any stderr from the server
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr else ""
            if stderr:
                print(f"Server stderr:\n{stderr}", file=sys.stderr)
        sys.exit(1)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
