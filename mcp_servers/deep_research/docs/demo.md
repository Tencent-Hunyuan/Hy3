# Demo Script

Use this script to record the required demo GIF or video.

## Setup

```bash
pip install ./mcp_servers/deep_research
cp mcp_servers/deep_research/.env.example .env
```

Edit `.env` with a working Hy3 endpoint and API key.

Verify the server over the real stdio protocol first:

```bash
python mcp_servers/deep_research/scripts/stdio_smoke.py
```

You should see `STDIO SMOKE OK` and a non-zero `SEARCH COUNT`.

## Demo 1: CodeBuddy / WorkBuddy

1. Add `mcp_servers/deep_research/examples/trae-codebuddy.mcp.json` to the
   client's MCP settings.
2. Open this repository.
3. Ask:

```text
Use the hy3-research MCP server to research this question:
"How does Hy3 compare to similar-size MoE models on agent benchmarks?"
Call research_question with searches "Hy3 agent benchmark, MoE SWE-Bench",
focus "benchmark numbers", depth "balanced", read_top_pages 2.
```

4. Show the `research_question` tool call and the Hy3 answer with citations.

## Demo 2: Cursor

1. Add `mcp_servers/deep_research/examples/cursor.mcp.json` to Cursor's MCP
   settings.
2. Ask:

```text
Use the hy3-research MCP server.
First call web_search_tool with query "Hy3 vLLM MTP serving".
Then call read_url_tool on the first result URL with max_chars 4000.
Then summarize_documents with question "What are the recommended vLLM flags?"
and documents set to the read_url_tool text.
```

3. Show the chained tool calls: `web_search_tool` -> `read_url_tool` ->
   `summarize_documents`.

## Client Scope

This branch documents practical setup for CodeBuddy/WorkBuddy and Cursor.
Trae, Qoder, Cline, Open WebUI, and other vibe-coding clients may support a
similar MCP stdio config, using `examples/cline_mcp_settings.json` as a template.

## Output to Attach

Attach the generated GIF/video to the PR or issue comment. The repository
intentionally does not commit large binary demo files.