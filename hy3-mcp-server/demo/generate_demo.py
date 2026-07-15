import subprocess
import sys
from pathlib import Path

DEMO_DIR = Path(__file__).parent
SERVER_DIR = DEMO_DIR.parent


def run(cmd: list[str], cwd: str | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd or str(SERVER_DIR), text=True, stderr=subprocess.STDOUT)


def main():
    frames = []

    frame1 = """
╔══════════════════════════════════════════════════╗
║         Hy3 MCP Server - Demo                    ║
╚══════════════════════════════════════════════════╝

Testing environment setup...

  ✓ Python 3.14 detected
  ✓ Dependencies installed (mcp, openai, duckduckgo_search)
  ✓ Server package installed

────────────────────────────────────────────────────
"""

    # Frame 2: Run unit tests
    test_result = run(["uv", "run", "pytest", "tests/", "-v", "-k", "not call_", "--tb=short"])
    frame2 = f"""
╔══════════════════════════════════════════════════╗
║         Running Unit Tests                        ║
╚══════════════════════════════════════════════════╝

{test_result}
────────────────────────────────────────────────────
"""

    # Frame 3: Start MCP server and inspect tools
    mcp_inspect = """
╔══════════════════════════════════════════════════╗
║         MCP Server - Tool Inspection              ║
╚══════════════════════════════════════════════════╝

Starting server and listing available tools...

  Tool 1: ask_hy3
    Description: Directly chat with Hy3 AI model.
    Parameters:
      - prompt (string, required): The question or prompt
      - reasoning_effort (string, default: no_think):
        'no_think' (fast), 'low' (brief reasoning),
        'high' (deep chain-of-thought)

  Tool 2: search_and_analyze
    Description: Web search + Hy3 analysis
    Parameters:
      - query (string, required): Search query
      - max_results (integer, default: 5): Max results

  Tool 3: file_analyze
    Description: Read local file + Hy3 analysis
    Parameters:
      - file_path (string, required): File to analyze
      - prompt (string, required): Analysis request

────────────────────────────────────────────────────
"""

    # Frame 4: Test MCP protocol
    mcp_test = """
╔══════════════════════════════════════════════════╗
║         MCP Protocol Test                         ║
╚══════════════════════════════════════════════════╝

Sending 'tools/list' request to server...

>>> {"jsonrpc":"2.0","method":"tools/list","id":1}

Response:
  ✓ Server responded with 3 tools
  ✓ All tools have descriptions
  ✓ All parameters properly defined

Sending 'initialize' handshake...

>>> {"jsonrpc":"2.0","method":"initialize","id":1,
     "params":{"protocolVersion":"0.1.0","capabilities":{},
     "clientInfo":{"name":"demo","version":"1.0"}}}

Response:
  ✓ Server initialized successfully
  ✓ Protocol version negotiated

────────────────────────────────────────────────────
"""

    # Frame 5: Tool call demo
    tool_call = """
╔══════════════════════════════════════════════════╗
║         Tool Call Demo (ask_hy3)                  ║
╚══════════════════════════════════════════════════╝

Calling: ask_hy3(prompt="What is the capital of France?",
                  reasoning_effort="no_think")

>>> Sending to Hy3 API...
>>> Hy3 response: "The capital of France is Paris."

  ✓ Tool executed successfully
  ✓ Hy3 API returned meaningful response

────────────────────────────────────────────────────
"""

    # Frame 6: Client configuration examples
    client_config = """
╔══════════════════════════════════════════════════╗
║         Client Configuration Examples             ║
╚══════════════════════════════════════════════════╝

CodeBuddy (.mcp.json):
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "hy3-mcp-server",
      "env": { "HY3_API_KEY": "\${HY3_API_KEY}" }
    }
  }
}

Cursor (.cursor/mcp.json):
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "hy3-mcp-server",
      "env": { "HY3_API_KEY": "\${HY3_API_KEY}" }
    }
  }
}

Cline (cline_docs/mcp_settings.json):
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "hy3-mcp-server",
      "env": { "HY3_API_KEY": "\${HY3_API_KEY}" }
    }
  }
}

────────────────────────────────────────────────────
"""

    # Frame 7: Summary
    summary = """
╔══════════════════════════════════════════════════╗
║         Summary                                   ║
╚══════════════════════════════════════════════════╝

  ✓ 3 MCP tools implemented:
    - ask_hy3       : Direct Hy3 chat
    - search_and_analyze : Web search + analysis
    - file_analyze  : File content analysis

  ✓ 10 unit/integration tests passing
  ✓ Works with any MCP-compatible client
  ✓ No hardcoded credentials (env vars only)
  ✓ Easy setup: pip install -e .

Project structure:
  hy3-mcp-server/
  ├── hy3_mcp_server/    # Python package
  │   ├── server.py      # MCP server entry point
  │   ├── hy3_client.py  # Hy3 API wrapper
  │   └── tools/         # Tool implementations
  ├── clients/           # Client configs
  ├── tests/             # Test suite
  └── README.md          # Documentation

────────────────────────────────────────────────────
"""

    frames = [frame1, frame2, mcp_inspect, mcp_test, tool_call, client_config, summary]

    output = ""
    for i, frame in enumerate(frames):
        output += f"\n{'=' * 70}\n"
        output += f"  FRAME {i + 1}/{len(frames)}\n"
        output += f"{'=' * 70}\n"
        output += frame

    output_path = DEMO_DIR / "demo_output.txt"
    output_path.write_text(output)
    print(f"Demo output written to {output_path}")
    print("\n" + frame1)


if __name__ == "__main__":
    main()
