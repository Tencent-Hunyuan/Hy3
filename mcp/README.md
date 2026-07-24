# Hy3 Deep Research MCP Server

An open-source, plug-and-play **MCP Server** that wraps the [Tencent Hunyuan Hy3](https://github.com/Tencent-Hunyuan/Hy3) API into a **Deep Research Assistant**. Any MCP-compatible AI client (CodeBuddy, WorkBuddy, Cursor, Cline, etc.) can connect with zero additional development.

## What It Does

The server exposes **3 MCP tools** that work together to conduct autonomous, multi-step research:

| Tool | Purpose | External Data Source |
|------|---------|---------------------|
| `search_web` | Search the web for up-to-date information | DuckDuckGo (no key) or Tavily (optional) |
| `fetch_url` | Extract clean main text from any web page | trafilatura |
| `deep_research` | Orchestrate full research: decompose → search → read → Hy3 synthesis | Hy3 API + both above |

### Research Pipeline

```
User Question
     │
     ▼
┌─────────────┐
│  Hy3 (low)  │  Decompose into sub-queries
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ search_web  │  Search each sub-query (DuckDuckGo/Tavily)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  fetch_url  │  Read full text of top sources
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Hy3 (high)  │  Synthesize report with [n] citations
└──────┬──────┘
       │
       ▼
  Structured Result
  (report + citations)
```

## Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** (recommended) or pip
- A **TokenHub API key** — get one at <https://console.cloud.tencent.com/tokenhub>

## Quick Start (One-Click Install)

### Option A: Using `uv` (recommended)

```bash
# Clone the repo and switch to the rhinobird2026 branch
git clone -b rhinobird2026 https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3/mcp

# Install in editable mode
uv pip install -e ".[dev]"

# Set your API key
export HUNYUAN_API_KEY="sk-your-key-here"   # Linux/macOS
set HUNYUAN_API_KEY=sk-your-key-here         # Windows CMD
$env:HUNYUAN_API_KEY="sk-your-key-here"      # Windows PowerShell

# Run the server
hy3-deep-research
```

### Option B: Using pip

```bash
git clone -b rhinobird2026 https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3/mcp

pip install -e ".[dev]"

export HUNYUAN_API_KEY="sk-your-key-here"
hy3-deep-research
```

### Option C: Install from pre-built package (no clone needed)

Pre-built wheel and sdist packages are in the `dist/` directory.

```bash
# From wheel (fastest — no build step)
pip install hy3_deep_research-0.1.0-py3-none-any.whl

# Or from sdist (source distribution)
pip install hy3_deep_research-0.1.0.tar.gz

# Set your API key, then run
export HUNYUAN_API_KEY="sk-your-key-here"
hy3-deep-research
```

### Option D: Run without installing (uvx)

```bash
uvx --from /path/to/Hy3/mcp hy3-deep-research
```

## Configuration

All configuration is via **environment variables only** — no API key is ever hardcoded.

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HUNYUAN_API_KEY` | **Yes** | — | TokenHub API key |
| `HUNYUAN_BASE_URL` | No | `https://tokenhub.tencentmaas.com/v1` | Hy3 API endpoint (TokenHub) |
| `HUNYUAN_MODEL` | No | `hy3` | Model name |
| `HUNYUAN_REASONING_FORMAT` | No | `top` | How `reasoning_effort` is passed: `top` (TokenHub) or `template` (self-deployed) |
| `TAVILY_API_KEY` | No | — | If set, uses Tavily instead of DuckDuckGo for search |
| `SEARCH_MAX_RESULTS` | No | `5` | Default max search results |
| `FETCH_MAX_CHARS` | No | `8000` | Max chars extracted per page |
| `FETCH_TIMEOUT` | No | `30` | Page fetch timeout (seconds) |
| `RESEARCH_MAX_SUB_QUERIES` | No | `3` | Max sub-queries Hy3 decomposes into |
| `RESEARCH_MAX_SOURCES` | No | `3` | Max sources to read in full |
| `RESEARCH_REASONING_EFFORT` | No | `high` | Default Hy3 reasoning depth for synthesis |

## Client Setup

Ready-to-use configuration files are in [`client_configs/`](./client_configs/). Pick the one for your client, replace `your-tokenhub-api-key-here` with your real key, and adjust the path to match your local clone.

### CodeBuddy / WorkBuddy

Place `codebuddy_mcp.json` as `.mcp.json` in your project root, or add via CLI:

```bash
# CLI approach
trae mcp add hy3-deep-research -- uvx --from /path/to/Hy3/mcp hy3-deep-research \
  -e HUNYUAN_API_KEY=sk-your-key \
  -e HUNYUAN_BASE_URL=https://tokenhub.tencentmaas.com/v1 \
  -e HUNYUAN_REASONING_FORMAT=top
```

Or create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "uvx",
      "args": ["--from", "/path/to/Hy3/mcp", "hy3-deep-research"],
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_MODEL": "hy3",
        "HUNYUAN_REASONING_FORMAT": "top"
      }
    }
  }
}
```

### Cursor

Create `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "uvx",
      "args": ["--from", "/path/to/Hy3/mcp", "hy3-deep-research"],
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_REASONING_FORMAT": "top"
      }
    }
  }
}
```

Then restart Cursor. The tools will appear in the MCP panel.

### Cline

Edit `cline_mcp_settings.json` in the Cline extension settings directory:

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "uvx",
      "args": ["--from", "/path/to/Hy3/mcp", "hy3-deep-research"],
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_REASONING_FORMAT": "top"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### Using `python -m` directly (no uv needed)

If you prefer not to use `uvx`, install the package with `pip install -e .` and use:

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "hy3-deep-research",
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_REASONING_FORMAT": "top"
      }
    }
  }
}
```

Or with `python -m`:

```json
{
  "mcpServers": {
    "hy3-deep-research": {
      "command": "python",
      "args": ["-m", "hy3_deep_research"],
      "env": {
        "HUNYUAN_API_KEY": "sk-your-key-here",
        "HUNYUAN_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HUNYUAN_REASONING_FORMAT": "top"
      }
    }
  }
}
```

## Tool Reference

### `search_web`

Search the web for up-to-date information.

**Parameters:**
- `query` (string, required) — The search query.
- `max_results` (int, default 5) — Maximum results to return (1–20).

**Returns:** `[{title, url, snippet}, ...]`

### `fetch_url`

Fetch a web page and extract its clean main text content. Only `http://` and `https://` URLs are accepted.

**Parameters:**
- `url` (string, required) — The full URL to fetch (http/https only).
- `max_chars` (int, default 8000) — Maximum characters of text to return.

**Returns:** `{url, title, content, success, error}`

### `deep_research`

Conduct deep research on a topic and produce a cited report.

**Parameters:**
- `query` (string, required) — The research question or topic.
- `max_search_results` (int, default 5) — Max web results per sub-query.
- `max_sources_to_fetch` (int, default 3) — Max URLs to read in full.
- `reasoning_effort` (string, default "high") — Hy3 reasoning depth: `no_think`, `low`, or `high`.

**Returns:** `{query, sub_queries, sources_searched, sources_fetched, report, citations}`

## Demo

### Demo Video

A demo video is included at [`demo/demo.mp4`](./demo/demo.mp4). It demonstrates:

1. The MCP server connected in WorkBuddy (3 tools visible).
2. Calling `search_web` to find web results.
3. Calling `fetch_url` to extract page content.
4. Calling `deep_research` to run the full pipeline: Hy3 decompose → search → fetch → Hy3 synthesis with `[n]` citations.

### Automated Demo Script

A ready-to-run demo script is provided in [`demo/demo_mcp_client.py`](./demo/demo_mcp_client.py). It spawns the MCP server as a subprocess, performs the MCP handshake, lists tools, and calls each one in sequence — exactly what a real MCP client does.

```bash
# Set your API key
export HUNYUAN_API_KEY="sk-your-key-here"

# Run the demo (uses a default query)
python demo/demo_mcp_client.py

# Or specify a custom research question
python demo/demo_mcp_client.py --query "What is Mixture of Experts in LLMs?"
```

The script will:
1. Start the MCP server and perform the `initialize` handshake.
2. Call `tools/list` to show all 3 registered tools.
3. Call `search_web` to find web results.
4. Call `fetch_url` to read the first result's full text.
5. Call `deep_research` to run the full pipeline and print the cited report.

### Deep Research in an MCP Client

Once the server is configured in your AI client, you can ask:

> "Use the deep_research tool to investigate: What are the key architectural innovations in Tencent Hunyuan Hy3?"

The client will:
1. Call `deep_research` with the query.
2. Hy3 decomposes it into sub-queries like `["Hy3 MoE architecture", "Hunyuan Hy3 technical report", "Hy3 reasoning capabilities"]`.
3. Each sub-query is searched on the web.
4. Top sources are fetched and read.
5. Hy3 synthesizes a report with inline `[1]`, `[2]` citations.

## Client Verification

This server has been verified in the following MCP clients:

| Client | Status | Config File |
|--------|--------|-------------|
| WorkBuddy | ✅ Verified | `client_configs/workbuddy_mcp.json` |
| Cursor | ✅ Verified | `client_configs/cursor_mcp.json` |
| Cline | ✅ Verified | `client_configs/cline_mcp_settings.json` |

## Verification with MCP Inspector

Test the server independently using the official MCP Inspector:

```bash
# Install MCP Inspector (if not already available)
npx @modelcontextprotocol/inspector

# Or point it directly at your server:
npx @modelcontextprotocol/inspector uvx --from /path/to/Hy3/mcp hy3-deep-research
```

Then open the Inspector UI (usually `http://localhost:6274`), connect, and test each tool.

## Project Structure

```
mcp/
├── pyproject.toml              # Package config, deps, entry point
├── .python-version             # Python 3.10
├── .env.example                # Environment variable template
├── Makefile                    # Dev convenience commands
├── README.md                   # This file
├── README_CN.md                # Chinese documentation
├── CHANGELOG.md                # Version history
├── client_configs/             # Ready-to-use MCP client configs
│   ├── codebuddy_mcp.json
│   ├── workbuddy_mcp.json
│   ├── cursor_mcp.json
│   ├── cline_mcp_settings.json
│   └── python_direct_mcp.json
├── demo/                       # Demo client + video
│   ├── demo_mcp_client.py      # Spawns server, calls all 3 tools
│   └── demo.mp4                # Demo video
├── src/
│   └── hy3_deep_research/
│       ├── __init__.py         # Package metadata + exports
│       ├── __main__.py         # `python -m hy3_deep_research` entry
│       ├── config.py           # Env-based configuration
│       ├── hy3_client.py       # Hy3 API wrapper (timeout + retry)
│       ├── models.py           # Pydantic data models
│       ├── server.py           # FastMCP server assembly + entry point
│       └── tools/
│           ├── __init__.py     # Tool exports
│           ├── search.py       # search_web tool
│           ├── fetch.py        # fetch_url tool (with timeout + URL validation)
│           └── research.py     # deep_research orchestration tool
├── tests/                      # Test suite
└── dist/                       # Pre-built packages
    ├── hy3_deep_research-0.1.0-py3-none-any.whl
    └── hy3_deep_research-0.1.0.tar.gz
```

## Reliability Features

- **Hy3 API calls**: 120s timeout, 3 retries with exponential backoff (1s/2s/4s) on `APITimeoutError`, `RateLimitError`, and `ConnectionError`.
- **Web page fetch**: configurable socket timeout (`FETCH_TIMEOUT`, default 30s) prevents hanging on unresponsive servers.
- **URL scheme validation**: `fetch_url` only accepts `http://` and `https://` URLs.
- **Search backoff**: DuckDuckGo failures retry up to 3 times with incremental delays.
- **Structured error handling**: all tools return structured results on failure, never crash the server.

## License

Apache License 2.0 — same as the parent [Hy3](https://github.com/Tencent-Hunyuan/Hy3) project.
