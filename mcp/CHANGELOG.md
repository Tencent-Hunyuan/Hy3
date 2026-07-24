# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-23

### Added
- Initial release of the Hy3 Deep Research MCP Server.
- Three MCP tools: `search_web`, `fetch_url`, `deep_research`.
- Web search via DuckDuckGo (no key) or Tavily (optional key).
- Clean text extraction via trafilatura with configurable timeout.
- Multi-step research pipeline: Hy3 decompose → search → fetch → Hy3 synthesis.
- Inline `[n]` citations in research reports.
- Hy3 API client with 120s timeout and 3-retry exponential backoff.
- TokenHub integration (replaces deprecated Hunyuan API endpoint).
- `HUNYUAN_REASONING_FORMAT` support: `top` (TokenHub cloud) / `template` (self-deployed).
- Client configuration files for CodeBuddy, WorkBuddy, Cursor, Cline.
- Automated demo client script (`demo/demo_mcp_client.py`).
- Demo video (`demo/demo.mp4`).
- Pydantic models as return type annotations for rich MCP JSON Schema.
- URL scheme validation (http/https only) in `fetch_url`.
- `reasoning_effort` parameter validation in `deep_research`.
- Logging to stderr (configurable via `HY3_LOG_LEVEL`).
- 34 pytest tests covering all components.
- Complete README in English and Chinese.
- Pre-built wheel and sdist packages in `dist/`.
