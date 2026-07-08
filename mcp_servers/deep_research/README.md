# Hy3 Deep Research MCP Server

`hy3-research-mcp` is a local stdio MCP Server that turns Hy3 into a **deep research assistant**: it searches the web, reads pages, and asks a Hy3 OpenAI-compatible endpoint to synthesize grounded, cited conclusions.

It is designed to be plug-and-play for any MCP client (Trae / CodeBuddy / Cursor / Cline / WorkBuddy / Qoder / Open WebUI ...). Web search uses DuckDuckGo HTML by default and **needs no extra API key**, so the server is useful the moment a Hy3 endpoint is configured.

## Scenario

A user asks a question. An MCP client (e.g. Cursor) is free to:

1. call `web_search_tool` to gather sources,
2. call `read_url_tool` to read a promising page,
3. call `research_question` to let Hy3 synthesize a cited answer, or
4. call `summarize_documents` / `generate_research_outline` for follow-ups.

Hy3 is the core reasoning engine; the web is the external data source.

## Tools

| Tool | Purpose | Key parameters |
| --- | --- | --- |
| `web_search_tool` | Search the web and return titles, URLs, snippets. No API key required (DuckDuckGo). | `query`, `max_results` |
| `read_url_tool` | Fetch a web page and return readable plain text. | `url`, `max_chars` |
| `research_question` | Search + (optional) page reads + Hy3 synthesis into a cited answer. | `question`, `searches`, `focus`, `depth`, `read_top_pages` |
| `summarize_documents` | Summarize pasted documents into a cited answer for a question. | `question`, `documents` |
| `generate_research_outline` | Generate a structured report outline grounded in live search evidence. | `question`, `searches` |

## Install

From this repository:

```bash
pip install ./mcp_servers/deep_research
```

For local development:

```bash
pip install -e ./mcp_servers/deep_research[dev]
```

After installation, the MCP server command is:

```bash
hy3-research-mcp
```

If you installed the package inside a conda environment, GUI clients may not inherit that environment's `PATH`. In that case, configure the client with the environment's Python executable:

```json
{
  "command": "/absolute/path/to/conda/envs/llms/bin/python",
  "args": ["-m", "hy3_research_mcp.server"]
}
```

## Configure Hy3 API

The server never hardcodes API keys. Use environment variables or a `.env` file.

When running from this repository, place `.env` in the repository root:

```bash
cp mcp_servers/deep_research/.env.example .env
```

The server searches for `.env` from the current working directory upward. You can also point to a specific file:

```bash
export HY3_ENV_FILE=/absolute/path/to/.env
```

Local vLLM/SGLang example:

```bash
HY3_BASE_URL=http://127.0.0.1:8000/v1
HY3_API_KEY=EMPTY
HY3_MODEL=hy3
HY3_TEMPERATURE=0.9
HY3_TOP_P=1.0
HY3_MAX_TOKENS=2048
HY3_REASONING_EFFORT=high
```

OpenRouter example:

```bash
HY3_BASE_URL=https://openrouter.ai/api/v1
HY3_API_KEY=sk-or-...
# OPENROUTER_API_KEY=sk-or-... also works when HY3_API_KEY is unset or EMPTY
HY3_MODEL=tencent/hy3:free
HY3_REASONING_EFFORT=high
```

Tencent Cloud Hunyuan example:

```bash
HY3_BASE_URL=https://api.hunyuan.cloud.tencent.com/v1
HUNYUAN_API_KEY=...
HY3_MODEL=hunyuan-turbos-latest
```

For OpenRouter, `HY3_REASONING_EFFORT=no_think` maps to `{"reasoning": {"effort": "none"}}`. For local vLLM/SGLang, it maps to Hy3 chat template kwargs.

## Web data source (optional)

`web_search_tool` defaults to DuckDuckGo HTML and needs no key. For richer results, set a search backend:

```bash
# Tavily
HY3_SEARCH_ENGINE=tavily
HY3_SEARCH_API_KEY=tvly-...
# or Brave
HY3_SEARCH_ENGINE=brave
HY3_SEARCH_API_KEY=...
HY3_MAX_SEARCH_RESULTS=5
HY3_PAGE_TIMEOUT=15
HY3_MAX_PAGE_CHARS=8000
```

(Tavily keys are also recognized as `TAVILY_API_KEY`; Brave as `BRAVE_API_KEY`.)

## Client Configuration

All MCP clients below use the same stdio server process. Prefer a project-level MCP config when the client supports it, and pass only `HY3_ENV_FILE` in the client config so API keys stay in your local `.env`.

### Trae / CodeBuddy

Use `examples/trae-codebuddy.mcp.json` as the shared stdio config template. See `docs/clients/trae-codebuddy.md` for setup details.

### Cursor

Add the server to `~/.cursor/mcp.json` (or the project-level `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "hy3-research": {
      "command": "/absolute/path/to/python",
      "args": ["-m", "hy3_research_mcp.server"],
      "env": { "HY3_ENV_FILE": "/absolute/path/to/Hy3/.env" }
    }
  }
}
```

### Cline / Qoder / Open WebUI

Any client that accepts an `mcpServers` block uses the same stdio shape as above.

## Tool Examples

### `web_search_tool`

```json
{ "query": "vLLM hy3 tool call parser", "max_results": 5 }
```

### `read_url_tool`

```json
{ "url": "https://github.com/Tencent-Hunyuan/Hy3", "max_chars": 8000 }
```

### `research_question`

```json
{
  "question": "How does Hy3 compare to GLM-5.1 on SWE-Bench Verified?",
  "searches": "Hy3 SWE-Bench Verified, GLM-5.1 SWE-Bench Verified",
  "focus": "benchmark numbers and scaffold variance",
  "depth": "balanced",
  "read_top_pages": 2
}
```

### `summarize_documents`

```json
{
  "question": "What are the deployment requirements?",
  "documents": ["...", "..."]
}
```

### `generate_research_outline`

```json
{ "question": "Designing a Hy3-powered agent for log triage", "searches": "MCP log triage, Hy3 agent tools" }
```
## Test

```bash
PYTHONPATH=mcp_servers/deep_research/src pytest -q mcp_servers/deep_research/tests
python -m py_compile mcp_servers/deep_research/src/hy3_research_mcp/*.py
# End-to-end over the real stdio protocol (hits the live web, no key needed):
python mcp_servers/deep_research/scripts/stdio_smoke.py
```

> `read_url_tool` extracts plain text from static HTML. JavaScript-rendered
> pages (e.g. some GitHub views) may return little text; prefer raw document
> URLs (e.g. `raw.githubusercontent.com/...`) for best results.

## Demo Recording Checklist

1. Install the package with `pip install ./mcp_servers/deep_research`.
2. Configure `.env` with Hy3 API settings.
3. Add the server to two MCP clients (e.g. CodeBuddy/WorkBuddy + Cursor).
4. In client 1, ask a question and show `research_question` returning a cited answer.
5. In client 2, show `web_search_tool` + `read_url_tool` + `summarize_documents`.
6. Record the screen as a GIF or video and attach it to the PR or issue comment.

## Safety Notes

- The server only reads URLs explicitly passed by the MCP client or derived from a search the client requested.
- Web pages are truncated by `HY3_MAX_PAGE_CHARS` before being sent to Hy3.
- API keys are read from environment variables or `.env`; they are not logged or returned by tools.
- stdio MCP servers must not write logs to stdout. This server does not print during normal operation.