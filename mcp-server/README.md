# Hy3 MCP Server - Deep Research Assistant

An MCP (Model Context Protocol) server that wraps [Hy3](https://github.com/Tencent-Hunyuan/Hy3) API capabilities into three composable tools for deep research workflows.

## Tools

| Tool | Description |
|------|-------------|
| `search_web` | DuckDuckGo search - returns top-5 results (title, URL, snippet) |
| `analyze_with_hy3` | Send content + question to Hy3 for in-depth analysis |
| `generate_report` | Ask Hy3 to synthesise findings into a structured Markdown report |

## Prerequisites

Deploy Hy3 locally with [vLLM](https://github.com/vllm-project/vllm) or [SGLang](https://github.com/sgl-project/sglang):

```bash
# vLLM example
vllm serve tencent/Hy3 --host 127.0.0.1 --port 8000
```

## Installation

```bash
# From source (recommended for development)
cd mcp-server
pip install -e .

# Or once published to PyPI
pip install hy3-mcp
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `HY3_API_BASE` | `http://127.0.0.1:8000/v1` | Hy3 OpenAI-compatible endpoint |
| `HY3_API_KEY` | `EMPTY` | API key (use `EMPTY` for local vLLM) |

## MCP Client Configuration

### Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hy3-research": {
      "command": "hy3-mcp",
      "env": {
        "HY3_API_BASE": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "EMPTY"
      }
    }
  }
}
```

### CodeBuddy / WorkBuddy

Project-level MCP config (`.codebuddy/mcp.json`):

```json
{
  "mcpServers": {
    "hy3-research": {
      "command": "hy3-mcp",
      "args": [],
      "env": {
        "HY3_API_BASE": "http://127.0.0.1:8000/v1",
        "HY3_API_KEY": "EMPTY"
      }
    }
  }
}
```

CLI add command:
```bash
codebuddy mcp add hy3-research --command "hy3-mcp" \
  --env HY3_API_BASE=http://127.0.0.1:8000/v1 \
  --env HY3_API_KEY=EMPTY
```

## Usage Examples

### Tool 1 - Search the web

```
Tool: search_web
Input: {"query": "transformer architecture 2024 advances"}
Output: Top-5 DuckDuckGo results with titles, URLs, and snippets
```

### Tool 2 - Analyze with Hy3

```
Tool: analyze_with_hy3
Input: {
  "content": "<paste search results or document here>",
  "question": "What are the main breakthroughs in 2024?",
  "reasoning": "high"
}
Output: Hy3's detailed analysis
```

### Tool 3 - Generate report

```
Tool: generate_report
Input: {
  "topic": "Transformer Architecture Advances in 2024",
  "findings": "<accumulated notes from search + analysis steps>"
}
Output: Complete Markdown research report
```

### Full research workflow example

A typical session with an MCP client:

1. `search_web(query="mixture of experts LLM 2024")`
2. `analyze_with_hy3(content=<results>, question="summarize key MoE innovations", reasoning="no_think")`
3. `search_web(query="MoE training efficiency benchmarks")`
4. `analyze_with_hy3(content=<results>, question="what do benchmarks show about efficiency gains?")`
5. `generate_report(topic="MoE LLM Advances 2024", findings=<combined notes>)`

## License

Apache 2.0 - see [LICENSE](../LICENSE)
