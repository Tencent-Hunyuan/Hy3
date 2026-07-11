# Hy3 Data MCP

[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](#license)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue?logo=typescript)](#)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green)](#)
[![Hy3](https://img.shields.io/badge/Powered%20by-Hy3-orange)](#)

A [Model Context Protocol](https://modelcontextprotocol.io) server that reads CSV, JSON, Excel, PDF, Word, and text files and turns them into charts, dashboards, word clouds, knowledge graphs, and analysis reports using the **Tencent Hunyuan Hy3** API.

Outputs are rendered as **SVG**, **HTML**, or **PNG**.

<video src="assets/demo.mp4" controls width="100%"></video>

![Demo](assets/demo.gif)

Built for the **2026 Tencent RhinoBird Open Source Talent Program** issue: [Build an MCP Server powered by Hy3](https://github.com/Tencent-Hunyuan/Hy3/issues/3).

---

## Rhinobird 2026 Submission

This repository is a submission for the [Tencent RhinoBird 2026 issue #3](https://github.com/Tencent-Hunyuan/Hy3/issues/3).

| Requirement                         | How this project meets it                                                                                                                   |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| MCP server powered by Hy3           | ✅ Implements a stdio MCP server using the TypeScript SDK; all analysis/planning tools call the Hy3 API.                                    |
| At least 3 tools                    | ✅ Exposes 11 tools, including `hy3_extract_document`, `hy3_analyze`, `hy3_render_chart`, `hy3_plan_dashboard`, etc.                        |
| External data sources/tools         | ✅ Reads local CSV/JSON/XLSX/PDF/DOCX/TXT files and renders charts with ECharts; no extra web services required.                            |
| Local stdio mode                    | ✅ Runs as a local stdio MCP server.                                                                                                        |
| No hard-coded API key               | ✅ API key is read from `HY3_API_KEY` environment variable only.                                                                            |
| Verified in 2+ MCP clients          | ✅ Tested with CodeBuddy / WorkBuddy, Cursor, Cline, Roo Code, Continue, Codex CLI, Claude Code, and OpenCode via the `hdm init` installer. |
| One-click installable package       | ✅ Distributed as `releases/hy3-data-mcp-0.3.11.tgz`; install with `npm install -g ./releases/hy3-data-mcp-0.3.11.tgz`.                     |
| README with install/config/examples | ✅ This README and `README_CN.md` provide installation, configuration, and usage examples.                                                  |
| Demo video/GIF                      | ✅ See the demo GIF and screenshot gallery below.                                                                                           |

**Selected scenario:** **Data analysis** — reading CSV/JSON/Excel + Hy3 analysis + chart/report generation from natural-language prompts.

---

## What it does

- **Chat-driven visualization** — Ask your MCP client to generate charts or dashboards from a data file or a prompt.
- **Hy3 plans, server renders** — `hy3_plan_*` tools use Hy3 to choose columns, titles, keywords, entities, and layouts; `hy3_render_*` tools draw the results without calling the model again.
- **Multiple output formats** — SVG for documents, HTML for interactive pages, PNG for slides or sharing.
- **Env-based configuration** — The API key is read from `HY3_API_KEY` in a local `.env` file; nothing is hard-coded.
- **Broad client support** — Works with CodeBuddy, WorkBuddy, Cline, Cursor, Roo Code, Continue, Codex CLI, OpenCode, and any stdio MCP client.

---

## Additional features

A few practical extras beyond the basic charting workflow:

- **Custom output filenames** — All render and report tools accept `output_filename`, so generated files can have meaningful names instead of random timestamps.
- **Source data table under charts** — `hy3_render_chart(..., show_data_table: true)` appends the raw data table to the HTML output for easy reference.
- **HTML theme switcher** — Switch themes interactively for single charts (`enable_theme_switcher`) and dashboards (`enable_theme_switcher`) without re-rendering.
- **Interactive WebGL 3D** — `bar3d`, `scatter3d`, and `line3d` default to WebGL scenes via ECharts GL (mouse drag to rotate, wheel to zoom, middle button to pan). Set `interactive_3d: false` to fall back to a static SVG pseudo-3D projection.
- **DOCX table extraction** — `hy3_extract_document` extracts tables from both PDF and DOCX files when `extract_tables: true`.
- **Statistical charts** — Native `violin` and `errorbar` chart types are rendered directly as SVG, no ECharts built-in required.
- **Dashboard KPI cards** — HTML dashboards automatically show Total / Average / Max / Min cards at the top (`show_kpi`).
- **Plan → Render pipeline** — Plan tools produce config that render tools consume directly, with automatic `value_column` fallback for `sunburst`/`treemap`.
- **Task-capable analysis tools** — Analyze and Plan tools are registered as MCP tasks with progress reporting, so long-running Hy3 calls stream updates back to the client.

---

## Features

`hy3-data-mcp` exposes **11 tools** split into three phases: **Extract & Analyze**, **Plan** (Hy3 decisions), and **Render** (deterministic output).

### Extract & Analyze (3 tools)

| Tool                   | What it does                                                                                                                                 | Output                   |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| `hy3_extract_document` | Extract raw text/tables from PDF, DOCX, TXT, CSV, JSON, and XLSX files. No model call. Adds `extract_tables` (PDF + DOCX) and `return_data`. | `json`                   |
| `hy3_analyze`          | General analysis that replaces the old `hy3_analyze_text` + `hy3_data_insight`. Supports `text` / `data` / `file_path`.                      | `text` / `html` / `json` |
| `hy3_analyze_report`   | Complete analysis report with Hy3-written insights and embedded charts. Params for charts, size, and theme.                                  | `html` / `markdown`      |

### Plan (Hy3 decision, 4 tools) → JSON

| Tool                       | What it does                                                   |
| -------------------------- | -------------------------------------------------------------- |
| `hy3_plan_chart`           | Recommend a suitable chart type, columns, and title from data. |
| `hy3_plan_dashboard`       | Design a multi-chart dashboard layout from structured data.    |
| `hy3_plan_wordcloud`       | Extract keywords and weights from text.                        |
| `hy3_plan_knowledge_graph` | Extract entities and relationships from text.                  |

### Render (pure rendering, 4 tools) → HTML / SVG / PNG

| Tool                         | What it does                                                                                                                                                                                                                      |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `hy3_render_chart`           | Render a single chart from explicit data + config. Adds `mark_point`, `mark_line`, `data_zoom`, `x_name`, `output_filename`, `show_data_table`, `enable_theme_switcher`, `interactive_3d` (default `true` for 3D HTML), and more. |
| `hy3_render_dashboard`       | Render a dashboard design into an interactive HTML page or PNG composite. Adds `show_kpi`, `enable_theme_switcher`, `output_filename`.                                                                                            |
| `hy3_render_wordcloud`       | Render a word cloud from explicit words or raw text.                                                                                                                                                                              |
| `hy3_render_knowledge_graph` | Render a knowledge graph from explicit nodes and links.                                                                                                                                                                           |

---

## Demo Gallery

All screenshots use the **Professional** theme and the bundled sample datasets.

<table>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/01-stacked-bar.png" width="420" alt="Stacked bar chart"><br/>Stacked bar by region</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/02-bubble.png" width="420" alt="Bubble chart"><br/>Age vs lifetime value</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/03-boxplot.png" width="420" alt="Boxplot"><br/>Clinical response boxplot</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/04-candlestick.png" width="420" alt="Candlestick chart"><br/>Stock candlestick</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/05-funnel.png" width="420" alt="Funnel chart"><br/>Marketing funnel</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/06-sunburst.png" width="420" alt="Sunburst chart"><br/>Geo/category sunburst</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/07-radar.png" width="420" alt="Radar chart"><br/>Department performance radar</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/08-wordcloud.png" width="420" alt="Word cloud"><br/>Keyword word cloud</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/09-knowledge-graph.png" width="420" alt="Knowledge graph"><br/>Knowledge graph</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/10-dashboard.png" width="420" alt="Dashboard"><br/>Composite dashboard</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/11-bar3d.png" width="420" alt="3D bar"><br/>3D bar by category</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/12-scatter3d.png" width="420" alt="3D scatter"><br/>3D scatter: units / revenue / profit</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/13-line3d.png" width="420" alt="3D line"><br/>3D line: units / revenue / profit</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/14-line_bar.png" width="420" alt="Line + bar"><br/>Line + bar combo</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/15-dual_axis.png" width="420" alt="Dual axis"><br/>Dual-axis combo</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/16-stacked_area.png" width="420" alt="Stacked area"><br/>Stacked area by region</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/17-grouped_line.png" width="420" alt="Grouped line"><br/>Grouped line by region</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/18-area_bar.png" width="420" alt="Area + bar"><br/>Area + bar combo</td>
  </tr>
  <tr>
    <td align="center" colspan="2"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/dashboard_2024_Sales___Profit_Dashboard_1783662671334.png" width="860" alt="2024 Sales & Profit Dashboard"><br/>2024 Sales &amp; Profit Dashboard (PNG composite)</td>
  </tr>
</table>

---

## Installation

Install the local release tarball globally:

```bash
npm install -g ./releases/hy3-data-mcp-0.3.11.tgz
```

Start the server:

```bash
hy3-data-mcp
```

Configure your MCP client:

```bash
hdm init
```

`hdm init` scans for installed MCP hosts such as Codex, Claude Code, Cursor, Cline, Roo Code, Continue and OpenCode, shows which are already configured, and lets you set up multiple clients in one run.

---

## Quick Start

### 1. Get an API key

Sign up at [TokenHub](https://tokenhub.tencentmaas.com) and create an API key for the Hy3 model.

### 2. Start the server

```bash
cp .env.example .env
# Edit .env and set HY3_API_KEY
hy3-data-mcp
```

### 3. Configure clients

The package ships with a dedicated `hdm` CLI for client configuration:

```bash
hdm init
```

`hdm init` scans your system for MCP clients (CodeBuddy, Cursor, Cline, Roo Code, Continue, Codex CLI, OpenCode, etc.), lets you pick one, and writes the MCP configuration and `.env` file automatically.

---

## Configuration

Create a `.env` file in the project root:

```dotenv
HY3_API_KEY=your-tokenhub-api-key
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3-preview
HY3_OUTPUT_DIR=./hy3-data-output
```

| Variable         | Required | Default                               | Description                      |
| ---------------- | -------- | ------------------------------------- | -------------------------------- |
| `HY3_API_KEY`    | Yes      | —                                     | Your TokenHub / Hy3 API key.     |
| `HY3_BASE_URL`   | No       | `https://tokenhub.tencentmaas.com/v1` | OpenAI-compatible endpoint.      |
| `HY3_MODEL`      | No       | `hy3-preview`                         | Model name.                      |
| `HY3_OUTPUT_DIR` | No       | `./hy3-data-output`                   | Where generated files are saved. |

---

## Long-running tools & async tasks

All tools delegate heavy work (column selection, chart design, summarization, etc.) to the Hy3 model. Complex prompts can take longer than the default MCP request timeout, so the server supports **MCP Task/Stream** execution:

- A task-aware client calls a tool with task augmentation and immediately receives a `taskId`.
- The server executes the tool in the background and updates task status.
- The client polls `tasks/get` for status and fetches the final result with `tasks/result`.
- Tasks can be cancelled with `tasks/cancel`.
- Clients that do not support tasks still work: `McpServer` automatically polls the task and returns the result synchronously.

Example with the experimental MCP client API:

```ts
const stream = client.experimental.tasks.callToolStream(
  {
    name: "hy3_analyze",
    arguments: {
      text: "...",
      question: "Summarize the risks",
      output_format: "text",
    },
  },
  CallToolResultSchema,
  { task: { ttl: 300_000 } }
);

for await (const message of stream) {
  if (message.type === "taskCreated") {
    console.log("taskId:", message.task.taskId);
  } else if (message.type === "taskStatus") {
    console.log("status:", message.task.status, message.task.statusMessage);
  } else if (message.type === "result") {
    console.log("result:", message.result);
  }
}
```

Task results are kept in memory for **5 minutes** by default and then cleaned up.

### How tasks are implemented

- **`McpServer` API** — The server uses the SDK's `McpServer` class instead of the low-level `Server` class. The SDK handles JSON Schema generation, argument validation, capability negotiation, and task protocol routing.
- **`taskSupport: "optional"`** — Every heavy tool is registered as task-capable but can still be called synchronously. Task-aware clients receive a `taskId` immediately; older clients rely on `McpServer`'s built-in auto-polling.
- **Cancellation** — The `AbortSignal` is threaded from the task runner through each tool and into the OpenAI SDK call, so `tasks/cancel` stops the in-flight model request.
- **1-second polling + 5-minute TTL** — The synchronous fallback polls every second, and a background sweeper removes completed tasks after 5 minutes to keep memory bounded.
- **Progress in task status** — `onProgress` updates are written to the task's `statusMessage`, so clients see messages like `"Executing 30/100"` instead of a silent timeout.
- **Streaming output** — Analysis and planning tools stream Hy3 tokens as they arrive. In Task/Stream mode, the latest accumulated output is written to `statusMessage`, so clients can preview the response before it is finalized.

## Design evolution

The original implementation tried to do everything in one synchronous call:

| Aspect                  | Before (v0.1.x black-box)                                               | After (v0.2.x transparent tasks)                                                                        |
| ----------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Interaction model       | One `tools/call` waits for the full model response                      | `taskId` returned immediately; client polls status and fetches result                                   |
| Timeout behavior        | Silent 60-second timeout, then failure                                  | No single-call timeout; tasks live up to 5 minutes                                                      |
| Cancellation            | Client can only abandon the call                                        | `AbortSignal` propagates to the OpenAI SDK; `tasks/cancel` stops the model request                      |
| Progress visibility     | None — the user stares at a spinner                                     | `statusMessage` is updated with progress and live model output preview                                  |
| Document analysis       | `hy3_document_summary` did extraction + analysis + rendering internally | `hy3_extract_document` → `hy3_analyze` → agent-saved data → `hy3_render_*` / `hy3_analyze_report` tools |
| Tool responsibility     | Mega-tools mixed reading, reasoning, and rendering                      | Each tool has a single responsibility and is composable by the agent                                    |
| Backwards compatibility | N/A — old clients use sync path                                         | `taskSupport: "optional"` means task-aware and legacy clients both work                                 |

### Benefits

1. **Avoids long request timeouts.** Returning a `taskId` immediately keeps the MCP client from holding an HTTP request open while Hy3 generates a long report, so the default 60-second timeout no longer blocks complex jobs.
2. **Shows progress.** The task runner writes incremental updates (`"Executing 30/100"`, partial JSON, partial report text) into `task.statusMessage`, so the wait is visible instead of silent.
3. **Supports cancellation.** The `AbortSignal` is threaded from `tasks/cancel` through the task runner, each tool, and into `openai.chat.completions.create`, so canceling stops the in-flight model request rather than only marking the task failed.
4. **Lets agents inspect intermediate results.** Splitting `hy3_document_summary` into `hy3_extract_document` + `hy3_analyze` lets the agent read raw text first, decide what structured data to extract, save it, and then choose the right visualization tool instead of relying on one monolithic tool.
5. **Streams analysis output.** For analysis tools, Hy3 tokens are consumed as they arrive and the running preview is pushed into the task status. A client using `callToolStream` can watch the answer being written in real time.

### How the design is implemented

- **`McpServer`** replaces the low-level `Server` class. The SDK now generates JSON Schema, validates arguments, routes requests, and handles the Task/Stream protocol, so the server code stays small and protocol-correct.
- **`server.experimental.tasks.registerToolTask`** with `execution: { taskSupport: "optional" }` registers every heavy tool as task-capable while preserving a synchronous fallback.
- **In-memory `TaskStore`** + `TaskMessageQueue` hold task metadata and results. A TTL sweeper removes completed tasks after 5 minutes.
- **`runToolAsTask`** runs the tool in the background, catches errors, stores results, and writes progress/status messages. Streaming tools receive an `onOutput` callback that updates the task status.
- **`Hy3Client.chatStream`** and **`askHy3Stream`** wrap the OpenAI SDK streaming completion API and accept an `AbortSignal`.
- **Tool split:** `hy3_extract_document` is a pure document parser; `hy3_analyze` handles text/data analysis with Hy3; `hy3_plan_*` tools produce JSON designs; `hy3_render_*` tools consume explicit data and configs without calling the model. This mirrors how a human analyst would work.

## Example workflow

Instead of one mega-tool that reads, extracts, analyzes, and renders in a single call, the tools are designed to be composed by capable MCP clients such as Codex, Claude Code, and Roo Code.

For a PDF report analysis request, the expected flow is:

```
1. hy3_extract_document(file_path="report.pdf")
   → { document_type: "pdf", text: "..." }

2. hy3_analyze(text="...", question="Extract key metrics and trends")
   → JSON with metrics and trends

3. Agent saves the JSON as report_data.csv

4. hy3_analyze_report(file_paths=["report_data.csv"], question="...")
   → detailed HTML/Markdown report

5. (optional) hy3_plan_dashboard(file_paths=["report_data.csv"])
   → JSON dashboard layout designed by Hy3

6. (optional) hy3_render_dashboard(file_paths=["report_data.csv"], design={...})
   → dashboard HTML/PNG
```

This split keeps each tool within a single responsibility, reduces timeouts, and lets the agent decide what to do based on the user's intent.

---

## Client Setup

### CodeBuddy / WorkBuddy

Add to `~/.codebuddy/mcp.json`:

```json
{
  "mcpServers": {
    "hy3-data-mcp": {
      "type": "stdio",
      "command": "hy3-data-mcp",
      "args": [],
      "env": {
        "HY3_API_KEY": "your-tokenhub-api-key",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3-preview",
        "HY3_OUTPUT_DIR": "./hy3-data-output"
      }
    }
  }
}
```

### Cline / Cursor / Roo Code / Continue

Use `hdm init` to auto-configure.

### Open WebUI

Open WebUI does not expose a stdio MCP host that `hdm init` can write to. To use Hy3 Data MCP there, create an Open WebUI [Function / Tool](https://docs.openwebui.com/features/plugin/functions/) that shells out to `hy3-data-mcp` and proxies JSON-RPC messages, or run the server separately and forward stdio over a pipe. An automatic installer for Open WebUI is not available yet.

---

## Usage Examples

### Extract document text

```json
{
  "name": "hy3_extract_document",
  "arguments": {
    "file_path": "./report.pdf",
    "max_text_length": 100000
  }
}
```

### Analyze extracted text

```json
{
  "name": "hy3_analyze",
  "arguments": {
    "text": "...",
    "question": "Summarize the key findings and risks",
    "output_format": "html",
    "language": "en"
  }
}
```

### Analyze structured data

```json
{
  "name": "hy3_analyze",
  "arguments": {
    "data_file_path": "./sales.csv",
    "question": "Find trends and outliers",
    "output_format": "text",
    "language": "en"
  }
}
```

### Plan a chart

```json
{
  "name": "hy3_plan_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "question": "Show monthly sales trend",
    "chart_type_hint": "line",
    "language": "en"
  }
}
```

### Render a chart from explicit config

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "bar",
    "x_column": "month",
    "y_column": "sales",
    "output_format": "png",
    "theme": "nature",
    "language": "zh"
  }
}
```

### Render a stacked bar chart

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "stacked_bar",
    "x_column": "month",
    "y_column": "sales",
    "group_column": "region",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Render a Sankey flow chart

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./flow.csv",
    "chart_type": "sankey",
    "x_column": "source",
    "y_column": "target",
    "value_column": "value",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Render a candlestick chart

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./stock.csv",
    "chart_type": "candlestick",
    "x_column": "date",
    "y_column": "close",
    "open_column": "open",
    "close_column": "close",
    "low_column": "low",
    "high_column": "high",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Plan a word cloud

```json
{
  "name": "hy3_plan_wordcloud",
  "arguments": {
    "file_path": "./reviews.csv",
    "max_words": 80,
    "language": "zh"
  }
}
```

### Render a word cloud

```json
{
  "name": "hy3_render_wordcloud",
  "arguments": {
    "file_path": "./reviews.csv",
    "max_words": 80,
    "output_format": "png",
    "language": "zh"
  }
}
```

### Plan a knowledge graph

```json
{
  "name": "hy3_plan_knowledge_graph",
  "arguments": {
    "file_path": "./article.txt",
    "max_entities": 30,
    "language": "en"
  }
}
```

### Render a knowledge graph

```json
{
  "name": "hy3_render_knowledge_graph",
  "arguments": {
    "nodes": "[{\"id\":\"A\",\"group\":1},{\"id\":\"B\",\"group\":2}]",
    "links": "[{\"source\":\"A\",\"target\":\"B\",\"relation\":\"links\"}]",
    "output_format": "png",
    "language": "en"
  }
}
```

### Plan a dashboard

```json
{
  "name": "hy3_plan_dashboard",
  "arguments": {
    "file_paths": ["./sales.csv", "./users.csv"],
    "title": "Monthly Operations Dashboard",
    "layout": "grid",
    "theme": "nature",
    "language": "en"
  }
}
```

### Render the dashboard design

```json
{
  "name": "hy3_render_dashboard",
  "arguments": {
    "file_paths": ["./sales.csv", "./users.csv"],
    "design": {
      "title": "Monthly Operations Dashboard",
      "layout": "grid",
      "charts": [
        {
          "file_index": 0,
          "chart_type": "bar",
          "x_column": "month",
          "y_column": "sales",
          "title": "Monthly Sales"
        }
      ]
    },
    "theme": "nature",
    "output_format": "html",
    "language": "en"
  }
}
```

### Generate a complete data analysis report

```json
{
  "name": "hy3_analyze_report",
  "arguments": {
    "file_paths": ["./sales.csv"],
    "question": "Analyze sales performance and highlight key drivers",
    "output_format": "html",
    "max_charts": 4,
    "theme": "professional",
    "language": "en"
  }
}
```

### 3D bar chart

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "bar3d",
    "x_column": "month",
    "y_column": "sales",
    "output_format": "png",
    "language": "en"
  }
}
```

### 3D scatter plot

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "scatter3d",
    "x_column": "price",
    "y_column": "sales",
    "z_column": "profit",
    "output_format": "png",
    "language": "en"
  }
}
```

### Dual-axis combo chart

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "dual_axis",
    "x_column": "month",
    "y_column": "sales",
    "value_column": "profit",
    "output_format": "png",
    "language": "en"
  }
}
```

### Render with ECharts option overrides

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "bar",
    "x_column": "month",
    "y_column": "sales",
    "overrides": "{\"title\":{\"text\":\"Custom Title\"}}",
    "output_format": "svg",
    "language": "en"
  }
}
```

---

## Output Formats

- **`svg`** — Lightweight, scalable, embeddable in reports or web pages.
- **`html`** — Interactive ECharts page with animations; open in any browser.
- **`png`** — Rasterized by `sharp`; suitable for slides, documents, and sharing.

---

## Themes & Fonts

Every visualization supports a `theme` parameter and an optional `font_family` override.

Built-in themes:

| Theme          | Style                                                                                           |
| -------------- | ----------------------------------------------------------------------------------------------- |
| `light`        | Clean white background with default ECharts palette.                                            |
| `dark`         | Dark background with high-contrast neon palette.                                                |
| `colorful`     | Vibrant palette for presentations.                                                              |
| `minimal`      | Subdued, single-hue friendly palette.                                                           |
| `professional` | Slate/grey palette for business reports.                                                        |
| `premium`      | Dark navy background with refined gradients, rounded shapes, and a modern professional palette. |
| `retro`        | Solarized-style warm palette with serif fonts.                                                  |
| `science`      | Green sequential palette with monospace fonts.                                                  |
| `nature`       | **Default.** Nature-journal style with a clean Tableau palette and readable typography.         |

Example with the default Nature theme and a custom font:

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "bar",
    "x_column": "month",
    "y_column": "sales",
    "output_format": "png",
    "theme": "nature",
    "font_family": "Inter",
    "language": "zh"
  }
}
```

### Custom Colors

Every visualization tool also accepts optional color overrides so you can match a brand or user preference:

| Parameter          | Description                                                                  |
| ------------------ | ---------------------------------------------------------------------------- |
| `background_color` | Chart/page background hex color, e.g. `#ffffff`.                             |
| `text_color`       | Title, label and legend text hex color, e.g. `#1a1a1a`.                      |
| `axis_color`       | Axis line and tick hex color, e.g. `#999999`.                                |
| `split_line_color` | Grid split-line hex color, e.g. `#e8e8e8`.                                   |
| `palette`          | Full custom palette as an array of hex colors.                               |
| `primary_color`    | Convenience shortcut: replaces the first color of the current theme palette. |

Example with a custom palette:

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "bar",
    "x_column": "month",
    "y_column": "sales",
    "output_format": "png",
    "theme": "nature",
    "palette": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
    "background_color": "#fafbfc",
    "text_color": "#222222",
    "font_family": "Inter"
  }
}
```

---

## Sample Datasets

The `sample_data/` directory contains both simple and complex datasets for testing every chart type.

Root sample files:

- `sample_data/sales.csv` — Simple monthly sales by region and product, good for bar, line, and area charts.
- `sample_data/stock.csv` — OHLC stock data for candlestick charts.
- `sample_data/reviews.csv` — Chinese product reviews for word clouds and sentiment analysis.
- `sample_data/article.txt` — A Chinese article about Tencent Hunyuan Hy3 for document summary tests.
- `sample_data/report.docx` — A sample Word document with a quarterly sales report and table, for testing document extraction and analysis.
- `sample_data/report.pdf` — The same report as a PDF file, for testing PDF parsing and text analysis.

`sample_data/complex/` datasets:

- `sample_data/complex/ecommerce_sales.csv` — 60 rows of multi-dimensional sales data (region, category, channel, revenue, profit, discount).
- `sample_data/complex/customers.csv` — 80 customer records with demographics, segment, LTV, and churn risk.
- `sample_data/complex/marketing_campaigns.csv` — 24 marketing campaigns with budget, impressions, clicks, conversions, and revenue.
- `sample_data/complex/clinical_trial.csv` — 90 patient records across three treatment groups for scientific analysis.
- `sample_data/complex/employee_performance.csv` — 60 employee records with department, level, salary, performance, and satisfaction.
- `sample_data/complex/hierarchical_geo_sales.csv` — Region → city → category hierarchical data for treemaps and sunbursts.
- `sample_data/complex/org_hierarchy.csv` — Division → department → team organization hierarchy for sunbursts and treemaps.
- `sample_data/complex/customer_3d.csv` — RFM-style customer segments (recency, frequency, monetary) for 3D scatter plots.
- `sample_data/complex/stock_kline.csv` — OHLCV stock data with trading volume for candlestick charts.
- `sample_data/complex/sankey_energy.csv` — Energy source → usage flow data for Sankey diagrams.
- `sample_data/complex/product_reviews.csv` — Product reviews for word clouds and sentiment analysis.
- `sample_data/complex/reviews.csv` — 20 realistic Chinese product reviews for word clouds and sentiment analysis.
- `sample_data/complex/knowledge_graph.json` — Nodes and edges for knowledge graph visualization.

Run `node scripts/generate-sample-data.mjs` to regenerate the CSV datasets deterministically. Run `python scripts/generate-sample-documents.py` (in a Python environment with `python-docx` and `fpdf2`) to regenerate the DOCX/PDF samples.

---

## End-to-End Example

Analyze the bundled e-commerce sales data and generate a complete HTML report:

```bash
# 1. Install and start the MCP server (see Quick Start above)
# 2. Call hy3_analyze_report with sample_data/complex/ecommerce_sales.csv
# 3. The report will be written to hy3-data-output/<YYYY-MM-DD>/html/data_report_<timestamp>.html
```

Or use the lower-level Plan → Render pipeline:

1. `hy3_plan_chart` on `sample_data/complex/ecommerce_sales.csv` to get a JSON chart plan.
2. `hy3_render_chart` with the plan fields to produce an SVG/PNG/HTML file.
3. `hy3_render_dashboard` with a `hy3_plan_dashboard` design to combine multiple charts.

All output files are organized under `hy3-data-output/<YYYY-MM-DD>/<ext>/` by date and file type.

---

## Parameter Quick Reference

| Parameter                               | Applies to                                                               | Notes                                                                                                           |
| --------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `data` / `data_file_path` / `file_path` | Most tools                                                               | Provide exactly one source. `data` is a JSON array string; `data_file_path`/`file_path` point to CSV/JSON/XLSX. |
| `theme`                                 | Render + report tools                                                    | One of `light`, `dark`, `colorful`, `minimal`, `professional`, `premium`, `retro`, `science`, `nature`.         |
| `language`                              | All Hy3 tools                                                            | `zh`, `en`, or `auto`. Auto detects from the question or data.                                                  |
| `output_format`                         | `hy3_render_chart`, `hy3_render_wordcloud`, `hy3_render_knowledge_graph` | `svg` (default), `html`, or `png`.                                                                              |
| `output_filename`                       | All writers                                                              | Optional base name; extension is added automatically.                                                           |
| `width` / `height`                      | Render tools + report                                                    | Range 200–2000 pixels.                                                                                          |
| `chart_type`                            | `hy3_render_chart`                                                       | 30+ supported types; required columns vary (see error messages).                                                |

---

## Troubleshooting

**MCP client times out on long analysis**

- `hy3_analyze`, `hy3_analyze_report`, and all Plan tools support async task execution. The server returns a `taskId` and streams progress; synchronous clients poll automatically.

**"Missing required column(s)" error**

- Check the error message for available columns. For composite charts (`dual_axis`, `line_bar`, etc.) make sure `value_column` is supplied; for `bubble` supply `size_column`; for 3D charts supply `z_column`.

**Model returns malformed JSON**

- Plan tools now retry internally and validate the model output against a schema. If parsing still fails, a fallback plan is returned with a `_warning` field explaining the situation.

**Output files pile up in one directory**

- Since v0.3.4, outputs are organized as `hy3-data-output/<YYYY-MM-DD>/<ext>/filename`.

**PNG rendering fails**

- Ensure Node.js ≥ 18 and that `@napi-rs/canvas` installed its native binary. On Windows, a clean `npm install` usually resolves canvas issues.

---

## Development

```bash
git clone https://github.com/xy200303/Hy3.git
cd Hy3/hy3-data-mcp
npm install
npm run build
npm test
npm run test:coverage   # generate coverage report
npm run test:real       # requires HY3_API_KEY
```

The test suite contains **174 unit, integration, and smoke tests** covering documents, utilities, themes, CLI config, dashboard rendering, client setup, streaming model output, async task execution, all visualization tools, chart rendering, and the MCP server handshake.

Debug with the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

---

## Roadmap

- [x] 11 core data analysis tools
- [x] SVG / HTML / PNG output formats
- [x] CLI installer (`hdm init`)
- [x] PDF, DOCX, XLSX, CSV, JSON, TXT document support
- [x] Multiple chart themes and custom font support
- [x] More dashboard layouts
- [x] Streaming progress for long-running analysis
- [x] Multi-language UI labels auto-detection
- [x] Shared Zod schemas across all tools
- [x] Robust model JSON output validation and retry
- [x] Input validation (file size, row limits, column checks)
- [x] Date/type organized output directory
- [x] K-line (candlestick) chart rendering fix
- [x] Dependency refresh and vulnerability cleanup

---

## License

This project is licensed under the [Apache-2.0](../LICENSE) license.
