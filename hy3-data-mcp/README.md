# Hy3 Data MCP

[![npm](https://img.shields.io/npm/v/hy3-data-mcp.svg)](https://www.npmjs.com/package/hy3-data-mcp)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](#license)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue?logo=typescript)](#)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green)](#)
[![Hy3](https://img.shields.io/badge/Powered%20by-Hy3-orange)](#)

> Turn any CSV, JSON, Excel, PDF, Word, or text file into charts, dashboards, word clouds, knowledge graphs, and AI-powered insights — all through an MCP server driven by **Tencent Hunyuan Hy3**.

**Hy3 Data MCP** is a [Model Context Protocol](https://modelcontextprotocol.io) server that brings analytical superpowers to your AI assistant. You ask questions in natural language; Hy3 reasons about the data, and the server renders publication-ready visuals in **SVG**, **HTML**, or **PNG**.

![Demo](https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/demo.gif)

Built for the **2026 Tencent RhinoBird Open Source Talent Program** issue: [Build an MCP Server powered by Hy3](https://github.com/Tencent-Hunyuan/Hy3/issues/3).

---

## Why Hy3 Data MCP?

- **No-code visualization for AI chats** — Your MCP client can now generate charts and dashboards from a single prompt.
- **Hy3 does the thinking** — Column selection, titles, keywords, entities, and layout decisions are delegated to the Hy3 model.
- **Production-grade outputs** — Static SVGs for documents, animated HTML pages for browsers, and PNG images for slides or social sharing.
- **Privacy-first** — Your API key lives only in a local `.env` file. Nothing is hard-coded or sent anywhere except the Hy3 endpoint.
- **Works everywhere** — Compatible with CodeBuddy, WorkBuddy, Cline, Cursor, Roo Code, Continue, Codex CLI, OpenCode, and any stdio MCP client.

---

## Features

| Tool | What it does | Output formats |
| --- | --- | --- |
| `hy3_data_visualize` | Bar, line, area, pie, donut, rose, scatter, bubble, scatter_trend, radar, heatmap, funnel, sankey, treemap, sunburst, gauge, histogram, boxplot, candlestick, stacked_bar, grouped_bar, 3D bar/scatter/line (bar3d/scatter3d/line3d), and composite charts (line_bar, area_bar, dual_axis, stacked_area, grouped_line). | `svg` / `html` / `png` |
| `hy3_wordcloud` | Extracts keywords with Hy3 and renders a word cloud. | `svg` / `html` / `png` |
| `hy3_knowledge_graph` | Extracts entities and relationships and renders a force-directed graph. | `svg` / `html` / `png` |
| `hy3_design_dashboard` | Designs a multi-chart dashboard layout from one or more files and returns a JSON plan. | `json` |
| `hy3_render_dashboard` | Renders a dashboard design into an interactive HTML page or PNG composite. | `html` / `png` |
| `hy3_data_report` | Generates a complete analysis report from a data file, with Hy3-written insights and embedded charts. | `html` / `markdown` |
| `hy3_data_insight` | Analyzes data and returns textual insights, trends, and outliers. | `text` |
| `hy3_extract_document` | Extracts raw text from PDF, DOCX, TXT, CSV, JSON, and XLSX files. No LLM. | `json` |
| `hy3_analyze_text` | Analyzes extracted text with Hy3 for summarization, extraction, or structured output. | `text` / `html` / `json` |

---

## Demo Gallery

All screenshots are rendered with the **Professional** theme using the bundled sample datasets.

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
npm install -g ./releases/hy3-data-mcp-0.2.2.tgz
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

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `HY3_API_KEY` | Yes | — | Your TokenHub / Hy3 API key. |
| `HY3_BASE_URL` | No | `https://tokenhub.tencentmaas.com/v1` | OpenAI-compatible endpoint. |
| `HY3_MODEL` | No | `hy3-preview` | Model name. |
| `HY3_OUTPUT_DIR` | No | `./hy3-data-output` | Where generated files are saved. |

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
    name: "hy3_analyze_text",
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

### Design highlights

- **High-level `McpServer` API** — We moved from the low-level `Server` class to `McpServer`, so the SDK handles JSON Schema generation, argument validation, capability negotiation, and task protocol routing for us.
- **`taskSupport: "optional"`** — Every tool is registered as task-capable, but still callable synchronously. Task-aware clients get a `taskId` immediately; older clients rely on `McpServer`'s built-in auto-polling, so nothing breaks.
- **Real cancellation** — The `AbortSignal` is threaded from the task runner through every tool and down to the OpenAI SDK call. Calling `tasks/cancel` actually stops the in-flight model request, not just the task status.
- **1-second polling + 5-minute TTL** — The synchronous fallback polls every second for responsiveness, while a background sweeper removes completed tasks after 5 minutes to keep memory bounded.
- **Live progress in task status** — While a tool runs, its `onProgress` updates are written to the task's `statusMessage`, so clients see messages like `"Executing 30/100"` instead of a silent timeout.
- **Streaming LLM output** — Analysis tools (`hy3_analyze_text`, `hy3_design_dashboard`, `hy3_data_insight`, `hy3_data_report`) stream Hy3 tokens as they are generated. In Task/Stream mode, the latest accumulated output is written to the task's `statusMessage`, so clients can preview the response before it is finalized.

## Design evolution: from black-box to transparent, agentic tasks

The original implementation tried to do everything in one synchronous call:

| Aspect | Before (v0.1.x black-box) | After (v0.2.x transparent tasks) |
| --- | --- | --- |
| Interaction model | One `tools/call` waits for the full LLM response | `taskId` returned immediately; client polls status and fetches result |
| Timeout behavior | Silent 60-second timeout, then failure | No single-call timeout; tasks live up to 5 minutes |
| Cancellation | Client can only abandon the call | `AbortSignal` propagates to the OpenAI SDK; `tasks/cancel` stops the model request |
| Progress visibility | None — the user stares at a spinner | `statusMessage` is updated with progress and live LLM output preview |
| Document analysis | `hy3_document_summary` did extraction + analysis + rendering internally | `hy3_extract_document` → `hy3_analyze_text` → agent-saved data → visualization/report tools |
| Tool responsibility | Mega-tools mixed reading, reasoning, and rendering | Each tool has a single responsibility and is composable by the agent |
| Backwards compatibility | N/A — old clients use sync path | `taskSupport: "optional"` means task-aware and legacy clients both work |

### Why this is better

1. **Timeouts become irrelevant.** By returning a `taskId` immediately, the MCP client never holds an HTTP request open while Hy3 generates a long report. The 60-second `DEFAULT_REQUEST_TIMEOUT_MSEC` no longer kills complex jobs.
2. **Users see progress.** The task runner writes incremental updates (`"Executing 30/100"`, partial JSON, partial report text) into `task.statusMessage`. This turns a black-box wait into a transparent, stream-like experience.
3. **Cancellation actually works.** Because the `AbortSignal` is threaded from `tasks/cancel` through the task runner, through each tool, and into `openai.chat.completions.create`, calling cancel aborts the in-flight model request instead of just marking the task failed.
4. **Agents can reason about intermediate results.** Splitting `hy3_document_summary` into `hy3_extract_document` + `hy3_analyze_text` lets the agent inspect raw text first, decide what structured data to extract, save it, and then choose the right visualization tool. The agent is no longer forced to trust a monolithic tool.
5. **Streaming analysis output.** For analysis tools, Hy3 tokens are consumed as they arrive and the running preview is pushed into the task status. A client using `callToolStream` sees the answer being written in real time, similar to ChatGPT.

### How the design is implemented

- **`McpServer`** replaces the low-level `Server` class. The SDK now generates JSON Schema, validates arguments, routes requests, and handles the Task/Stream protocol, so the server code stays small and protocol-correct.
- **`server.experimental.tasks.registerToolTask`** with `execution: { taskSupport: "optional" }` registers every heavy tool as task-capable while preserving a synchronous fallback.
- **In-memory `TaskStore`** + `TaskMessageQueue` hold task metadata and results. A TTL sweeper removes completed tasks after 5 minutes.
- **`runToolAsTask`** runs the tool in the background, catches errors, stores results, and writes progress/status messages. Streaming tools receive an `onOutput` callback that updates the task status.
- **`Hy3Client.chatStream`** and **`askHy3Stream`** wrap the OpenAI SDK streaming completion API and accept an `AbortSignal`.
- **Agentic tool split:** `hy3_extract_document` is a pure document parser; `hy3_analyze_text` is the only LLM analysis tool that takes text; `hy3_design_dashboard` produces a JSON layout; `hy3_render_dashboard` and other rendering tools only consume structured files and designs. This mirrors how a human analyst would work.

## Agentic workflow

Instead of one mega-tool that reads, extracts, analyzes, and renders in a single call, the tools are designed to be composed by capable MCP clients such as Codex, Claude Code, and Roo Code.

For a PDF report analysis request, the expected flow is:

```
1. hy3_extract_document(file_path="report.pdf")
   → { document_type: "pdf", text: "..." }

2. hy3_analyze_text(text="...", question="Extract key metrics and trends")
   → JSON with metrics and trends

3. Agent saves the JSON as report_data.csv

4. hy3_data_report(file_paths=["report_data.csv"], question="...")
   → detailed HTML/Markdown report

5. (optional) hy3_design_dashboard(file_paths=["report_data.csv"])
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

Open WebUI does not expose a stdio MCP host that `hdm init` can write to. To use Hy3 Data MCP there, create an Open WebUI [Function / Tool](https://docs.openwebui.com/features/plugin/functions/) that shells out to `hy3-data-mcp` and proxies JSON-RPC messages, or run the server separately and forward stdio over a pipe. A one-click installer for Open WebUI is not available yet.

---

## Usage Examples

### Analyze and visualize a CSV

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "bar",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Sankey flow chart

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "sankey",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Scientific boxplot

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "boxplot",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Bubble chart with size dimension

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "bubble",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Stacked bar chart

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "stacked_bar",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Histogram

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "histogram",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Candlestick / K-line chart

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./stock.csv",
    "chart_type": "candlestick",
    "output_format": "png",
    "language": "zh"
  }
}
```

### Design a dashboard from multiple files

```json
{
  "name": "hy3_design_dashboard",
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
        { "file_index": 0, "chart_type": "bar", "x_column": "month", "y_column": "sales", "title": "Monthly Sales" }
      ]
    },
    "theme": "nature",
    "output_format": "html",
    "language": "en"
  }
}
```

### Extract insights from text data

```json
{
  "name": "hy3_wordcloud",
  "arguments": {
    "file_path": "./reviews.csv",
    "column": "comment",
    "max_words": 80,
    "output_format": "png",
    "language": "zh"
  }
}
```

### Extract and analyze a document

First extract the raw text:

```json
{
  "name": "hy3_extract_document",
  "arguments": {
    "file_path": "./report.pdf"
  }
}
```

Then analyze the extracted text:

```json
{
  "name": "hy3_analyze_text",
  "arguments": {
    "text": "...",
    "question": "Summarize the key findings and risks",
    "output_format": "html",
    "language": "en"
  }
}
```

### Generate a complete data analysis report

```json
{
  "name": "hy3_data_report",
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
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "bar3d",
    "output_format": "png",
    "language": "en"
  }
}
```

### 3D scatter plot

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
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
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "dual_axis",
    "x_column": "month",
    "y_column": "sales",
    "value_column": "profit",
    "output_format": "png",
    "language": "en"
  }
}
```

---

## Output Formats

- **`svg`** — Lightweight, scalable, embeddable in reports or web pages.
- **`html`** — Interactive ECharts page with animations; open in any browser.
- **`png`** — Rasterized by `sharp`; perfect for slides, documents, and sharing.

---

## Themes & Fonts

Every visualization supports a `theme` parameter and an optional `font_family` override.

Built-in themes:

| Theme | Style |
| --- | --- |
| `light` | Clean white background with default ECharts palette. |
| `dark` | Dark background with high-contrast neon palette. |
| `colorful` | Vibrant palette for presentations. |
| `minimal` | Subdued, single-hue friendly palette. |
| `professional` | Slate/grey palette for business reports. |
| `premium` | Dark navy background with refined gradients, rounded shapes, and a modern professional palette. |
| `retro` | Solarized-style warm palette with serif fonts. |
| `science` | Green sequential palette with monospace fonts. |
| `nature` | **Default.** Nature-journal style with a publication-ready Tableau palette and clean typography. |

Example with the default Nature theme and a custom font:

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "bar",
    "output_format": "png",
    "theme": "nature",
    "font_family": "Inter",
    "language": "zh"
  }
}
```

### Custom Colors

Every visualization tool also accepts optional color overrides so you can match a brand or user preference:

| Parameter | Description |
| --- | --- |
| `background_color` | Chart/page background hex color, e.g. `#ffffff`. |
| `text_color` | Title, label and legend text hex color, e.g. `#1a1a1a`. |
| `axis_color` | Axis line and tick hex color, e.g. `#999999`. |
| `split_line_color` | Grid split-line hex color, e.g. `#e8e8e8`. |
| `palette` | Full custom palette as an array of hex colors. |
| `primary_color` | Convenience shortcut: replaces the first color of the current theme palette. |

Example with a custom palette:

```json
{
  "name": "hy3_data_visualize",
  "arguments": {
    "file_path": "./sales.csv",
    "chart_type": "bar",
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

The `sample_data/` directory contains both simple and complex datasets for testing every chart type:

- `sample_data/complex/ecommerce_sales.csv` — 60 rows of multi-dimensional sales data (region, category, channel, revenue, profit, discount).
- `sample_data/complex/customers.csv` — 80 customer records with demographics, segment, LTV, and churn risk.
- `sample_data/complex/marketing_campaigns.csv` — 24 marketing campaigns with budget, impressions, clicks, conversions, and revenue.
- `sample_data/complex/clinical_trial.csv` — 90 patient records across three treatment groups for scientific analysis.
- `sample_data/complex/employee_performance.csv` — 60 employee records with department, level, salary, performance, and satisfaction.
- `sample_data/complex/hierarchical_geo_sales.csv` — Region → city → category hierarchical data for treemaps and sunbursts.
- `sample_data/complex/reviews.csv` — 20 realistic Chinese product reviews for word clouds and sentiment analysis.
- `sample_data/stock.csv` — OHLC stock data for candlestick charts.
- `sample_data/report.docx` — A sample Word document with a quarterly sales report and table, for testing `hy3_extract_document` and `hy3_analyze_text`.
- `sample_data/report.pdf` — The same report as a PDF file, for testing PDF parsing and text analysis.

Run `node scripts/generate-sample-data.mjs` to regenerate the CSV datasets deterministically. Run `python scripts/generate-sample-documents.py` (in a Python environment with `python-docx` and `fpdf2`) to regenerate the DOCX/PDF samples.

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

The test suite contains **135 unit, integration, and smoke tests** covering documents, utilities, themes, CLI config, dashboard rendering, client setup, streaming LLM output, async task execution, all visualization tools, chart rendering, and the MCP server handshake. As of the latest run, code coverage for the `src/` directory is approximately **95% statements / 85% branches / 96% functions** (overall ~92% statements when including uncovered helper scripts).

Debug with the [MCP Inspector](https://github.com/modelcontextprotocol/inspector):

```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

---

## Roadmap

- [x] 7 core data analysis tools
- [x] SVG / HTML / PNG output formats
- [x] CLI installer (`hdm init`)
- [x] PDF, DOCX, XLSX, CSV, JSON, TXT document support
- [x] Multiple chart themes and custom font support
- [x] More dashboard layouts
- [x] Streaming progress for long-running analysis
- [x] Multi-language UI labels auto-detection

---

## License

This project is licensed under the [Apache-2.0](../LICENSE) license.
