# Validation notes

## Recorded validation

The included `demo.gif` is a reproducible integration smoke test recorded with the
official MCP Inspector CLI 0.21.2. It verifies:

- MCP stdio initialization;
- discovery of all four tools through `tools/list`;
- a real `tools/call` request to `analyze_evidence`;
- the production OpenAI-compatible client path; and
- a successful structured MCP result with source metadata.

The machine used for this recording exposed `qwen3.6-35b-a3b`, not Hy3. The GIF therefore
demonstrates MCP protocol and compatible-API integration only; it is not evidence of Hy3
model-quality validation.

## Re-record against Hy3

Start a real Hy3 vLLM/SGLang endpoint, then run:

```bash
cd mcp_servers/hy3_deep_research
export HY3_BASE_URL="http://127.0.0.1:8000/v1"
export HY3_MODEL="hy3"
export HY3_API_KEY="EMPTY"
export HY3_REASONING_EFFORT="high"

uv run --with pillow scripts/record_inspector_demo.py
```

The same script invokes the official Inspector CLI for both `tools/list` and `tools/call`.

The bundled recording uses an English prompt so it renders correctly even in minimal
containers without CJK fonts. To record Chinese output, install a CJK font such as Noto
Sans CJK, or set `MCP_DEMO_FONT` to a local `.ttf`, `.otf`, or `.ttc` font path before
running the recorder.

## Other lightweight validation options

- Protocol + dummy backend: `uv run pytest -q ../../test/test_hy3_mcp_integration.py`
- Interactive Inspector UI: `npx -y @modelcontextprotocol/inspector uv run hy3-deep-research`
- CodeBuddy CLI: use `examples/codebuddy.mcp.json` without installing the CodeBuddy IDE.

