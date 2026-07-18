# Real client verification

These demonstrations were recorded on 2026-07-11 against the local `hy3-knowledge` stdio MCP
server. From the package directory, the equivalent server command is
`uvx --from . hy3-knowledge-mcp`; remote answers used OpenRouter model route `tencent/hy3:free`
with `reasoning_effort=none`.

The tested clients were:

- Cline CLI `3.0.39` — [recording excerpt](cline.gif)
- TRAE SOLO CN `0.1.25` / VS Code `1.107.1` — [recording excerpt](trae.gif)

Both clients received this exact prompt:

```text
必须通过 hy3-knowledge MCP 完成，不要直接读取文件替代工具：
1. 调用 hy3_kb_index_documents，collection="demo"，path="."。
2. 调用 hy3_kb_list_sources 确认来源。
3. 调用 hy3_kb_search 搜索“两个客户端验证对应哪一天上线”。
4. 调用 hy3_kb_ask 回答同一问题。
5. 最终展示调用过的工具名称、答案和文件/行号引用。
```

Each run visibly connected to `hy3-knowledge` and invoked all four requested tools:
`hy3_kb_index_documents`, `hy3_kb_list_sources`, `hy3_kb_search`, and `hy3_kb_ask`. The expected and
observed answer was `2025-11-18`, cited as `738b65bbd428/roadmap.md, lines 1–8`.

Credentials were supplied only through the launching process environment and were not stored in
client configuration or the published excerpts. The GIFs are cropped excerpts from real screen
recordings; they are not simulated animations. The published frames were manually reviewed for
secrets, personal paths, usernames, personal notifications, and unrelated task names. Tests pin the
reviewed files by SHA-256 so later asset replacement requires another explicit review.

[Back to the English README](../../README.md) · [返回中文 README](../../README_CN.md)
