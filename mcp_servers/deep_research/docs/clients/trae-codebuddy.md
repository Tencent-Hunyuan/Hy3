# Trae / CodeBuddy MCP Configuration

Trae and CodeBuddy use the same local stdio MCP server configuration. Keep one
shared template and paste it into whichever client UI or project config you use.

The current hands-on examples are scoped to Trae and CodeBuddy. Cursor, Qoder,
Cline, WorkBuddy, and other clients are not claimed as practiced yet, but use the
same stdio shape.

## Install

From the Hy3 repository root:

```bash
conda activate llms
pip install -e ./mcp_servers/deep_research[dev]
```

Confirm the package is installed in the conda environment:

```bash
python -c "import hy3_research_mcp; print(hy3_research_mcp.__file__)"
```

## Configure API Credentials

Create `.env` in the Hy3 repository root:

```bash
cp mcp_servers/deep_research/.env.example .env
```

For OpenRouter:

```bash
HY3_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
HY3_MODEL=tencent/hy3:free
HY3_REASONING_EFFORT=high
```

For local vLLM/SGLang:

```bash
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
HY3_REASONING_EFFORT=high
```

Web search uses DuckDuckGo by default and needs no key. Do not paste API keys
into client MCP config. The server reads them from `HY3_ENV_FILE`.

## Shared MCP Config

Use `examples/trae-codebuddy.mcp.json` as the template:

```json
{
  "mcpServers": {
    "hy3-research": {
      "command": "/absolute/path/to/conda/envs/llms/bin/python",
      "args": ["-m", "hy3_research_mcp.server"],
      "env": {
        "HY3_ENV_FILE": "/absolute/path/to/Hy3/.env"
      }
    }
  }
}
```

## Client Notes

Trae:
- Add the shared server block through Trae's MCP settings UI or project-level
  MCP config if your version supports it.
- Use the same command, args, and `HY3_ENV_FILE` environment variable.

CodeBuddy:
- CodeBuddy's local MCP config commonly lives at `~/.codebuddy/mcp.json`.
- Merge the `hy3-research` entry under `mcpServers`, or add the same stdio
  server through CodeBuddy's UI if available.

## Tool Call Demo

Prompt:

```text
Use the hy3-research MCP server to research this question:
"How does Hy3 compare to similar-size MoE models on agent benchmarks?"
Call research_question with:
- question: "How does Hy3 compare to similar-size MoE models on agent benchmarks?"
- searches: "Hy3 agent benchmark, MoE model SWE-Bench Verified"
- focus: "benchmark numbers and agent scaffolding variance"
- depth: "balanced"
- read_top_pages: 2
```

Expected tool:

```json
{
  "tool": "research_question",
  "arguments": {
    "question": "How does Hy3 compare to similar-size MoE models on agent benchmarks?",
    "searches": "Hy3 agent benchmark, MoE model SWE-Bench Verified",
    "focus": "benchmark numbers and agent scaffolding variance",
    "depth": "balanced",
    "read_top_pages": 2
  }
}
```

The client is free to call `web_search_tool` and `read_url_tool` first to gather
sources, then `research_question` to let Hy3 synthesize a cited answer.

## stdio Verification (no client needed)

Before recording a demo, verify the server is callable over the real stdio
protocol with the SDK client:

```bash
pip install -e ./mcp_servers/deep_research[dev]
python mcp_servers/deep_research/scripts/stdio_smoke.py
```

This drives `web_search_tool` and `read_url_tool` against the live web and
prints `STDIO SMOKE OK` when the round trip succeeds.