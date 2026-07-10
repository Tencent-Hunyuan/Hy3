# PR Description / 提交说明

## Title / 标题

feat(hy3-data-mcp): 2.0 architecture with Extract → Analyze → Plan → Render split

---

## Summary / 摘要

This PR introduces the major 2.0 refactor of `hy3-data-mcp`. The tool surface is now organized into four explicit phases — **Extract**, **Analyze**, **Plan**, and **Render** — separating static file handling from LLM reasoning and from deterministic rendering.

本次 PR 对 `hy3-data-mcp` 进行 2.0 大版本重构。工具面被重新组织为四个明确阶段 —— **提取**、**分析**、**规划**、**渲染** —— 将静态文件处理、LLM 推理与确定性渲染解耦。

### What changed / 改动概览

- **Extract (1 tool)** — `hy3_extract_document` parses PDF, DOCX, TXT, CSV, JSON, XLSX with optional table extraction hints and structured data return.
- **Analyze (2 tools)** — `hy3_analyze` replaces `hy3_analyze_text` and `hy3_data_insight`, accepting text or structured data. `hy3_analyze_report` replaces `hy3_data_report`.
- **Plan (4 tools)** — `hy3_plan_chart`, `hy3_plan_dashboard`, `hy3_plan_wordcloud`, and `hy3_plan_knowledge_graph` use Hy3 to produce JSON designs consumed by the render tools.
- **Render (4 tools)** — `hy3_render_chart`, `hy3_render_wordcloud`, `hy3_render_knowledge_graph`, and `hy3_render_dashboard` render directly from explicit data + config without calling the LLM.
- **Tool count** — the server now exposes **11 tools**.
- **Version** — bumped to `0.3.0`.
- **No root-level Zod `.refine()`** — parameter validation is performed inside run functions to keep `inputSchema` compatible with CodeBuddy.
- **Extended chart rendering** — `hy3_render_chart` supports subtitle, legend position, axis names, grid/tooltip toggles, line smooth/symbol/area, bar stack, markPoint, markLine, dataZoom, and a JSON `overrides` field merged into the generated ECharts option.

---

## Before vs. After: why the new design wins / 前后对比：新方案赢在哪里

| Dimension / 维度 | Before (v0.2.x) / 之前 | After (v0.3.x) / 现在 |
| --- | --- | --- |
| Tool taxonomy / 工具分类 | Mixed LLM + rendering in one tool | Clear Extract → Analyze → Plan → Render phases |
| Chart rendering / 图表渲染 | `hy3_data_visualize` called Hy3 to choose columns | `hy3_render_chart` is deterministic; `hy3_plan_chart` produces the config |
| Word cloud / 词云 | `hy3_wordcloud` mixed keyword extraction + rendering | `hy3_plan_wordcloud` extracts; `hy3_render_wordcloud` renders |
| Knowledge graph / 知识图谱 | `hy3_knowledge_graph` mixed extraction + rendering | `hy3_plan_knowledge_graph` extracts; `hy3_render_knowledge_graph` renders |
| Dashboard / 大屏 | `hy3_design_dashboard` returned JSON; rendering was separate but naming inconsistent | `hy3_plan_dashboard` + `hy3_render_dashboard` naming is symmetric with other plan/render pairs |
| Validation / 参数校验 | Root-level Zod `.refine()` produced empty `inputSchema` for some clients | Validation moved into run functions; schema stays clean |
| Overrides / 自定义选项 | Limited chart styling | Rich render config + JSON `overrides` merged into ECharts option |

### Key insight / 核心洞察

The previous generation mixed planning and rendering inside the same tool call, which made it hard for agents to inspect or reuse intermediate designs. The 2.0 architecture makes every intermediate artifact explicit: agents can validate a plan, edit it, save it, and then render — or render directly if they already know the configuration.

上一代把规划与渲染混合在同一个工具调用里，导致 Agent 难以检查或复用中间设计。2.0 架构让每个中间产物都显式化：Agent 可以验证、编辑、保存规划结果，再执行渲染；也可以在已知配置时直接渲染。

---

## Design techniques / 设计技巧

1. **Static vs. LLM tool split**
   - `hy3_extract_document` and all `hy3_render_*` tools are registered as synchronous, non-LLM tools.
   - All `hy3_analyze*` and `hy3_plan*` tools remain task-capable via `server.experimental.tasks.registerToolTask` with `taskSupport: "optional"`.

2. **`loadInputData` helper**
   - `src/utils.ts` now exposes `loadInputData({ data, data_file_path, file_path })` so plan/analyze/render tools accept the same three input forms consistently.

3. **Chart validation in run functions**
   - `hy3_render_chart` validates required columns per chart type (e.g., `size_column` for bubble, `group_column` for stacked bar, OHLC for candlestick) and throws clear errors instead of relying on Zod `.refine()`.

4. **ECharts option overrides**
   - `src/viz/echarts.ts` extends `ChartConfig` with rich styling options and deep-merges a JSON `overrides` string into the generated option, allowing arbitrary ECharts customization.

5. **Backward compatibility note**
   - Old tool names (`hy3_data_visualize`, `hy3_wordcloud`, `hy3_knowledge_graph`, `hy3_data_report`, `hy3_data_insight`, `hy3_analyze_text`, `hy3_design_dashboard`) are removed in this major release because the 2.0 phase split provides a cleaner, more composable surface.

---

## Verification / 验证

```bash
npm install
npm run build
npm test
```

- **145 tests passed** across 14 test files.
- Coverage for `src/` remains approximately **95% statements / 85% branches / 96% functions**.
- Real-API smoke tests available with `HY3_API_KEY` via `npm run test:real`.

---

## Version / 版本

Bumped to `0.3.0` and packaged as `releases/hy3-data-mcp-0.3.0.tgz`.

---

## Files worth reviewing / 重点审阅文件

- `src/server.ts` — version bump and `McpServer` setup
- `src/tools/index.ts` — registration of all 11 new tools
- `src/tools/extractDocument.ts` — extraction with optional table/structured-data hints
- `src/tools/analyze.ts` — unified text/data analysis
- `src/tools/analyzeReport.ts` — renamed and extended report generation
- `src/tools/planChart.ts`, `src/tools/planDashboard.ts`, `src/tools/planWordcloud.ts`, `src/tools/planKnowledgeGraph.ts` — LLM planning tools
- `src/tools/renderChart.ts`, `src/tools/renderWordcloud.ts`, `src/tools/renderKnowledgeGraph.ts`, `src/tools/renderDashboard.ts` — deterministic rendering tools
- `src/utils.ts` — `loadInputData`, `loadInputText`, and shared helpers
- `src/viz/echarts.ts` — extended `ChartConfig` and `buildEChartsOption`
- `README.md` / `README_CN.md` — updated tool list, examples, and workflow descriptions

---

## Notes for reviewers / 审阅提示

- PDF/DOCX table extraction is exposed via the `extract_tables` parameter but is not fully implemented: PDF tables currently return an empty `tables` array with a note.
- The task store remains in-memory for simplicity; persistence can be added without changing the public tool interface.
- MCP Task/Stream is still an experimental SDK API; interfaces may change in future SDK versions.
