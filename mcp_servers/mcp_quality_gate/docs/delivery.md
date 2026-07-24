# Delivery Verification / 交付验证

## Acceptance contract

Stage 8 is complete only when all of the following are backed by reproducible,
sanitized evidence:

1. a clean source install builds and passes typecheck, lint, tests, and evaluation;
2. `npm pack` contains only intended runtime, documentation, example, evaluation,
   and demo files;
3. the tarball installs in an empty directory and exposes the package executable;
4. the installed executable completes an MCP handshake, lists four tools, and
   performs one deterministic fixture call;
5. Cursor reads the project configuration, reports the server ready, and exposes
   every public tool argument;
6. CodeBuddy reads the project configuration at project scope and connects;
7. each client performs at least one read-only fixture tool call after explicit
   approval;
8. English and Chinese installation, safety, and runnable-call documentation is
   present;
9. a demo GIF is derived from the sanitized verification transcript;
10. no committed configuration, transcript, image metadata, or report contains a
    credential, token, personal home path, or private registry.

阶段 8 只有在上述 10 项都有可复现、已脱敏证据时才算完成。工具被客户端发现
不等于已经完成 `tools/call`；验证记录必须明确区分 `configured`、`ready`、
`tools discovered` 和 `fixture called`。

## Reproducible commands

From `mcp_servers/mcp_quality_gate`:

```bash
npm ci
npm run typecheck
npm run lint
npm test
npm run evaluate
npm run demo
npm run verify:delivery
npm run verify:release
npm pack --dry-run
```

`verify:release` intentionally fails while either official client has not
completed its read-only fixture call. This prevents a `ready` or `connected`
health result from being mistaken for complete Stage 8 evidence.

For a clean tarball installation, create a new temporary directory outside the
repository, install the generated `.tgz`, start the installed bin with
`MCPQ_TARGETS_FILE` pointing to the packaged example registry, then use an MCP
client to list tools and call `mcpq_inspect_server`.

## Evidence rules

- Record the date, operating system, architecture, client version, package
  version, tarball SHA-256, configuration scope, tool count, tool names, and call
  result.
- Keep concise normalized outputs, not raw provider conversations or logs.
- Replace repository and home paths with `<repo>` and `<home>` before committing.
- Never record environment values. It is sufficient to state whether a required
  variable was present.
- Do not claim a model-mediated call if authentication prevented the call.
- The GIF must show only synthetic fixture IDs and normalized results.

## Known boundary

The delivery demo proves client integration and deterministic fixture behavior. It
does not prove that every third-party MCP Server is safe, that a semantic model is
always correct, or that generated probes are safe to execute. Probe execution
remains outside the product.
