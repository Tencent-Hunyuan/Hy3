# hy3-mcp FAQ

## What does this server provide?

hy3-mcp is an MCP stdio server exposing five tools backed by Hy3:
review_code (code review), ask_docs (knowledge-base Q&A), analyze_data
(CSV/JSON analysis), deep_research (multi-source synthesis) and hy3_status
(diagnostics without any LLM call).

## How do I run it without an API key?

Configure nothing, or set HY3_MCP_OFFLINE=1: the server then uses a
deterministic fake Hy3 backend, so every tool works offline and each reply
is clearly labeled with an OFFLINE DEMO MODE banner.

## Which environment variables select the real backend?

Set HY3_API_BASE to an OpenAI-compatible Hy3 endpoint (self-hosted
vLLM/SGLang or Tencent cloud) and HY3_API_KEY when the endpoint requires
one. HY3_MODEL defaults to "hy3".

## Where do the extra data sources live?

Local file reading is sandboxed under HY3_MCP_ROOT. Web search is pluggable
via HY3_SEARCH_PROVIDER: the default "offline" stub needs no network, while
"tavily" performs real search using the TAVILY_API_KEY environment variable.
