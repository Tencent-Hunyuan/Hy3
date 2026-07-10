# PR Description / 提交说明

## Title / 标题

feat(hy3-data-mcp): async Task/Stream execution, streaming LLM output, and agentic tool split

---

## Summary / 摘要

This PR upgrades `hy3-data-mcp` from a synchronous, monolithic "black-box" design to an asynchronous, transparent, agentic architecture built on MCP Task/Stream.

本次 PR 将 `hy3-data-mcp` 从同步、单体的“黑盒”设计升级为基于 MCP Task/Stream 的异步、透明、可编排架构。

### What changed / 改动概览

- **Migrated to `McpServer`** — the high-level MCP SDK API now handles schema generation, argument validation, capability negotiation, and task protocol routing.
- **MCP Task/Stream async execution** — heavy tools return a `taskId` immediately and run in the background; clients poll status and fetch results.
- **Real cancellation** — `AbortSignal` propagates from `tasks/cancel` through the task runner and into the OpenAI SDK call.
- **Streaming LLM output** — analysis tools push live Hy3 tokens into the task `statusMessage`, so clients can preview answers before they are finalized.
- **Agentic tool split** — removed `hy3_document_summary` and `hy3_document_visualize`; introduced `hy3_extract_document` + `hy3_analyze_text` so agents can reason over intermediate results.

---

## Before vs. After: why the new design wins / 前后对比：新方案赢在哪里

| Dimension / 维度 | Before (v0.1.x) / 之前 | After (v0.2.x) / 现在 |
| --- | --- | --- |
| Interaction model / 交互模式 | One `tools/call` blocks until the LLM finishes | Returns `taskId` immediately; client polls `tasks/get` and fetches `tasks/result` |
| Timeout behavior / 超时表现 | Hit the 60s MCP default timeout on long reports | No single-call timeout; tasks live up to 5 minutes |
| Cancellation / 取消机制 | Client could only abandon the call | `AbortSignal` reaches OpenAI SDK; `tasks/cancel` aborts the running model request |
| Progress visibility / 进度可见性 | Silent spinner / 黑盒转圈 | `statusMessage` shows execution progress and live output preview |
| Document analysis / 文档分析 | `hy3_document_summary` did extraction + analysis + rendering internally | `hy3_extract_document` → `hy3_analyze_text` → agent-saved data → visualization/report tools |
| Tool responsibility / 工具职责 | Mega-tools mixed reading, reasoning, and rendering | Single-responsibility tools composed by the agent |
| Backwards compatibility / 向后兼容 | No task support | `taskSupport: "optional"` keeps sync path working for legacy clients |

### Key insight / 核心洞察

The old design treated the LLM call as an opaque RPC: send a file, wait, hope it finishes before the timeout. The new design treats each heavy operation as a **long-running job** with explicit lifecycle, progress, and cancellation — and lets the agent see intermediate outputs so it can make better decisions.

旧方案把 LLM 调用当成一个不透明的 RPC：发一个文件，等，祈祷在超时前完成。新方案把每个重操作都当作一个有明确生命周期、进度和取消能力的**长时任务**，同时让 Agent 看到中间产物，从而做出更好的决策。

---

## Design techniques / 设计技巧

1. **High-level `McpServer` API**
   - Replaced the low-level `Server` class with `McpServer`. The SDK now generates JSON Schema from Zod, validates arguments, routes `tools/call`, and implements `tasks/*` handlers automatically. The server code is smaller and protocol-correct.

2. **`taskSupport: "optional"`**
   - Every heavy tool is registered with `server.experimental.tasks.registerToolTask(..., { execution: { taskSupport: "optional" } })`. Task-aware clients get async execution; older clients still receive a synchronous response via `McpServer`'s built-in auto-polling.

3. **In-memory task store + TTL sweeper**
   - `TaskStore` holds task metadata and results. A background sweeper removes completed tasks after 5 minutes to keep memory bounded. Swapping the store for Redis/DB later is a one-file change.

4. **`AbortSignal` threading**
   - The signal from `tasks/cancel` travels: `task runner` → `handleToolCall` → individual tool → `Hy3Client.chat` / `chatStream` → `openai.chat.completions.create(..., { signal })`. This makes cancellation real, not cosmetic.

5. **Streaming output for analysis tools**
   - `Hy3Client.chatStream` yields tokens. `askHy3Stream` consumes them and forwards an `onOutput` callback. The task runner writes the running preview into `taskStore.updateTaskStatus`, so a Task/Stream client sees the answer being written live.

6. **Agentic tool composition**
   - `hy3_extract_document` only parses files (no LLM). `hy3_analyze_text` only analyzes text. Rendering tools only consume structured files. This mirrors a human analyst's workflow and lets the agent reuse intermediate artifacts.

---

## Verification / 验证

```bash
npm install
npm run build
npm test
```

- **134 tests passed** across 14 test files.
- Coverage for `src/` is approximately **95% statements / 85% branches / 96% functions**.
- Real-API smoke tests available with `HY3_API_KEY` via `npm run test:real`.

---

## Version / 版本

Bumped to `0.2.1` and packaged as `releases/hy3-data-mcp-0.2.1.tgz`.

---

## Files worth reviewing / 重点审阅文件

- `src/server.ts` — `McpServer` setup with task capabilities
- `src/client.ts` — `chat()` and `chatStream()` with `AbortSignal`
- `src/tools/index.ts` — tool registration (static vs. task-capable)
- `src/tasks/runner.ts` — background task execution and streaming status updates
- `src/tasks/store.ts` — in-memory task store
- `src/tools/extractDocument.ts` — new static document extraction tool
- `src/tools/analyzeText.ts` — new streaming text analysis tool
- `README.md` / `README_CN.md` — updated design highlights and agentic workflow

---

## Notes for reviewers / 审阅提示

- MCP Task/Stream is still an experimental SDK API; interfaces may change in future SDK versions.
- The task store is currently in-memory for simplicity. Persistence can be added without changing the public tool interface.
- Old tools `hy3_document_summary` and `hy3_document_visualize` were removed because their functionality is now better expressed as the extract → analyze → render chain.
