# Hy3 数据分析 MCP

[![npm](https://img.shields.io/npm/v/hy3-data-mcp.svg)](https://www.npmjs.com/package/hy3-data-mcp)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](#license)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue?logo=typescript)](#)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green)](#)
[![Hy3](https://img.shields.io/badge/Powered%20by-Hy3-orange)](#)

> 让任意 CSV、JSON、Excel、PDF、Word 或文本文件，通过 **腾讯混元 Hy3** 驱动的 MCP 服务器，一键变成图表、数据大屏、词云、知识图谱和 AI 洞察。

**Hy3 数据分析 MCP** 是一个基于 [Model Context Protocol](https://modelcontextprotocol.io) 的服务端，它让你的 AI 助手拥有数据分析能力：你用自然语言提问，Hy3 完成推理，服务端渲染出可用于报告、网页或演示的 **SVG**、**HTML** 或 **PNG** 可视化结果。

![Demo](https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/demo.gif)

本项目为 **2026 腾讯犀牛鸟开源人才培养活动** issue [Build an MCP Server powered by Hy3](https://github.com/Tencent-Hunyuan/Hy3/issues/3) 而开发。

---

## 为什么选择 Hy3 数据分析 MCP？

- **对话即可视化** —— 在 MCP 客户端里一句话就能生成图表、词云、知识图谱或数据大屏。
- **Hy3 负责思考** —— 字段选择、标题生成、关键词抽取、实体关系识别、大屏布局都交给 Hy3 模型的 `hy3_plan_*` 工具完成。
- **多种输出格式** —— SVG 适合嵌入文档，HTML 可交互浏览，PNG 可直接放入 PPT 或社交媒体分享。
- **隐私优先** —— API Key 仅保存在本地 `.env` 文件中，代码中不硬编码任何密钥，也不会把数据发送到其他第三方服务。
- **兼容主流客户端** —— 支持 CodeBuddy、WorkBuddy、Cline、Cursor、Roo Code、Continue、Codex CLI、OpenCode 等任意 stdio MCP 客户端。

---

## ✨ 亮点功能 —— 本分支的差异化特性

除了标准的 MCP 数据可视化流程，本分支还针对实际使用场景做了大量增强：

- **自定义输出文件名** —— 所有渲染/报告类工具都支持 `output_filename`，让生成的文件拥有有意义的名称，而不是随机时间戳。
- **图表下方展示源数据表** —— `hy3_render_chart(..., show_data_table: true)` 会在 HTML 页面底部附上原始数据表格，便于核对与分享。
- **HTML 主题切换器** —— 单图表（`enable_theme_switcher`）和仪表盘（`enable_theme_switcher`）都支持在页面上实时切换主题。
- **交互式 WebGL 3D** —— `bar3d`、`scatter3d`、`line3d` 默认通过 ECharts GL 渲染真正的 WebGL 场景：鼠标拖拽旋转、滚轮缩放、中键平移；设置 `interactive_3d: false` 可回退为静态 SVG 伪 3D 投影。
- **DOCX 表格提取** —— `hy3_extract_document` 开启 `extract_tables: true` 后，可同时从 PDF 和 DOCX 中抽取表格。
- **统计图表类型** —— 原生支持 `violin`（小提琴图）和 `errorbar`（误差棒图），采用自定义 SVG 渲染。
- **仪表盘 KPI 卡片** —— HTML 仪表盘默认在顶部展示总计 / 平均 / 最大 / 最小四张 KPI 卡片（`show_kpi`）。
- **Plan → Render 流水线** —— Plan 工具生成的配置可直接被 Render 工具消费，并针对 `sunburst`/`treemap` 自动处理 `value_column` 回退。
- **任务化 LLM 工具** —— 分析与 Plan 工具注册为 MCP Task，支持进度上报，让长时间 Hy3 调用也能实时反馈给客户端。

---

## 🧠 混元 Hy3 在哪些环节参与？

Hy3 数据分析 MCP 被刻意拆分为 **LLM 驱动** 和 **确定性** 两个阶段，这样你能清楚知道何时调用了混元大模型，何时只是服务端在纯渲染。

| 阶段 | 工具 | 是否调用 Hy3 | Hy3 扮演的角色 |
| --- | --- | --- | --- |
| **提取** | `hy3_extract_document` | ❌ 否 | 纯文件解析（PDF、DOCX、XLSX、CSV、JSON、TXT）。不调用模型，无 API 费用。 |
| **Plan** | `hy3_plan_chart`、`hy3_plan_dashboard`、`hy3_plan_wordcloud`、`hy3_plan_knowledge_graph` | ✅ 是 | 查看数据/文本，决定图表类型、坐标轴、字段、标题、主题、仪表盘布局、关键词、实体与关系。 |
| **分析** | `hy3_analyze`、`hy3_analyze_report` | ✅ 是 | 阅读内容，撰写洞察、结论与报告正文，并推荐最能讲故事的图表。 |
| **渲染** | `hy3_render_chart`、`hy3_render_dashboard`、`hy3_render_wordcloud`、`hy3_render_knowledge_graph` | ❌ 否 | 根据显式配置确定性渲染。快速、可复现、不调用模型。 |

一句话概括：**Hy3 负责思考，服务端负责画图。** Plan 与分析工具注册为 MCP Task，支持可选的进度流式上报，因此长时间的模型调用不会阻塞客户端。

---

## 功能特性

`hy3-data-mcp` 共提供 **11 个工具**，按三个阶段组织：**提取 & 分析**、**Plan（LLM 决策）**、**Render（纯渲染）**。

### 📄 提取 & 分析（3 个）

| 工具 | 功能 | 输出 |
| --- | --- | --- |
| `hy3_extract_document` | 从 PDF、DOCX、TXT、CSV、JSON、XLSX 中提取原始文本/表格，不调用 LLM。新增 `extract_tables`（支持 PDF + DOCX）、`return_data`。 | `json` |
| `hy3_analyze` | 通用分析，合并了旧 `hy3_analyze_text` + `hy3_data_insight`。支持 `text` / `data` / `file_path`。 | `text` / `html` / `json` |
| `hy3_analyze_report` | 一站式分析报告，含 Hy3 撰写的洞察与嵌入式图表。支持图表数、尺寸、主题等丰富参数。 | `html` / `markdown` |

### 🧠 Plan（LLM 决策，4 个）→ 输出 JSON

| 工具 | 功能 |
| --- | --- |
| `hy3_plan_chart` | 推荐最佳图表类型、列、标题。 |
| `hy3_plan_dashboard` | 设计仪表盘大屏布局。 |
| `hy3_plan_wordcloud` | 提取关键词 + 权重。 |
| `hy3_plan_knowledge_graph` | 提取实体 + 关系。 |

### 🎨 Render（纯渲染，4 个）→ 输出 HTML / SVG / PNG

| 工具 | 功能 |
| --- | --- |
| `hy3_render_chart` | 渲染单图表。新增 `mark_point`、`mark_line`、`data_zoom`、`x_name`、`output_filename`、`show_data_table`、`enable_theme_switcher`、`interactive_3d`（3D HTML 默认 `true`）等丰富配置。 |
| `hy3_render_dashboard` | 渲染仪表盘大屏。新增 `show_kpi`、`enable_theme_switcher`、`output_filename`。 |
| `hy3_render_wordcloud` | 渲染词云。 |
| `hy3_render_knowledge_graph` | 渲染知识图谱。 |

---

## 效果图展示

以下截图均使用 **Professional** 专业主题，基于仓库内置示例数据集直接渲染生成。

<table>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/01-stacked-bar.png" width="420" alt="堆叠柱状图"><br/>分区域堆叠柱状图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/02-bubble.png" width="420" alt="气泡图"><br/>年龄与生命周期价值</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/03-boxplot.png" width="420" alt="箱线图"><br/>临床试验响应分数箱线图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/04-candlestick.png" width="420" alt="K 线图"><br/>股票价格 K 线图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/05-funnel.png" width="420" alt="漏斗图"><br/>营销转化漏斗</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/06-sunburst.png" width="420" alt="旭日图"><br/>区域/城市/品类旭日图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/07-radar.png" width="420" alt="雷达图"><br/>部门绩效雷达图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/08-wordcloud.png" width="420" alt="词云"><br/>关键词词云</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/09-knowledge-graph.png" width="420" alt="知识图谱"><br/>知识图谱</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/10-dashboard.png" width="420" alt="数据大屏"><br/>综合数据大屏</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/11-bar3d.png" width="420" alt="3D 柱状图"><br/>3D 各品类营收</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/12-scatter3d.png" width="420" alt="3D 散点图"><br/>3D 销量-营收-利润散点</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/13-line3d.png" width="420" alt="3D 折线图"><br/>3D 销量-营收-利润折线</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/14-line_bar.png" width="420" alt="折线+柱状组合图"><br/>月度营收与利润组合图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/15-dual_axis.png" width="420" alt="双轴组合图"><br/>品类营收利润双轴图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/16-stacked_area.png" width="420" alt="堆叠面积图"><br/>各区域月度营收堆叠面积图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/17-grouped_line.png" width="420" alt="分组折线图"><br/>各区域月度营收分组折线</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/18-area_bar.png" width="420" alt="面积+柱状组合图"><br/>月度利润与营收面积柱状图</td>
  </tr>
  <tr>
    <td align="center" colspan="2"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/dashboard_2024_Sales___Profit_Dashboard_1783662671334.png" width="860" alt="2024 销售与利润大屏"><br/>2024 销售与利润数据大屏（PNG 合成图）</td>
  </tr>
</table>

---

## 安装

将本地安装包全局安装：

```bash
npm install -g ./releases/hy3-data-mcp-0.3.9.tgz
```

启动 MCP 服务：

```bash
hy3-data-mcp
```

配置 MCP 客户端：

```bash
hdm init
```

`hdm init` 会自动扫描已安装的 MCP 宿主，如 Codex、Claude Code、Cursor、Cline、Roo Code、Continue、OpenCode 等，显示每个宿主的已配置/未配置状态，并支持一次性为多个客户端写入配置。

---

## 快速开始

### 1. 获取 API Key

前往 [TokenHub](https://tokenhub.tencentmaas.com) 注册并创建 Hy3 模型的 API Key。

### 2. 启动 MCP 服务

```bash
cp .env.example .env
# 编辑 .env，填入 HY3_API_KEY
hy3-data-mcp
```

### 3. 一键配置客户端

包内附带独立的 `hdm` CLI，用于自动配置 MCP 客户端：

```bash
hdm init
```

`hdm init` 会扫描系统中的 MCP 客户端（CodeBuddy、Cursor、Cline、Roo Code、Continue、Codex CLI、OpenCode 等），让你选择目标客户端，并自动写入 MCP 配置和 `.env` 文件。

---

## 配置说明

在项目根目录创建 `.env` 文件：

```dotenv
HY3_API_KEY=your-tokenhub-api-key
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3-preview
HY3_OUTPUT_DIR=./hy3-data-output
```

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `HY3_API_KEY` | 是 | — | TokenHub / Hy3 API Key。 |
| `HY3_BASE_URL` | 否 | `https://tokenhub.tencentmaas.com/v1` | OpenAI 兼容接口地址。 |
| `HY3_MODEL` | 否 | `hy3-preview` | 模型名。 |
| `HY3_OUTPUT_DIR` | 否 | `./hy3-data-output` | 生成文件的输出目录。 |

---

## 长耗时工具与异步任务

所有工具都会把重活（选列、图表设计、文档总结等）交给 Hy3 模型处理。复杂提示词可能超过 MCP 默认的 60 秒请求超时，因此本服务器支持 **MCP Task/Stream** 异步执行：

- 支持任务的客户端调用工具时带上任务增强参数，服务端立即返回 `taskId`。
- 服务端在后台执行工具，并不断更新任务状态。
- 客户端通过 `tasks/get` 轮询状态，通过 `tasks/result` 获取最终结果。
- 可通过 `tasks/cancel` 取消任务。
- 不支持任务的旧客户端仍可正常使用：`McpServer` 会自动轮询任务并以同步方式返回结果。

使用实验性 MCP 客户端 API 的示例：

```ts
const stream = client.experimental.tasks.callToolStream(
  {
    name: "hy3_analyze",
    arguments: {
      text: "...",
      question: "总结风险点",
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
    console.log("状态:", message.task.status, message.task.statusMessage);
  } else if (message.type === "result") {
    console.log("结果:", message.result);
  }
}
```

任务结果默认在内存中保留 **5 分钟**，之后自动清理。

### 设计亮点

- **高阶 `McpServer` API** —— 从低层 `Server` 迁移到 `McpServer`，由 SDK 自动完成 JSON Schema 生成、参数校验、能力协商和任务协议路由，代码更简洁。
- **`taskSupport: "optional"`** —— 每个工具都注册为任务型工具，但仍支持同步调用。支持任务的客户端立即获得 `taskId`，旧客户端由 `McpServer` 内置自动轮询，完全兼容。
- **真正的取消机制** —— `AbortSignal` 从任务执行器一路透传到各个工具，最终传递到 OpenAI SDK 调用。调用 `tasks/cancel` 会真正中断正在进行的模型请求，而不只是改状态。
- **1 秒轮询 + 5 分钟 TTL** —— 同步回退场景每秒轮询，保证响应速度；后台定时清理 5 分钟前的已完成任务，防止内存无限增长。
- **实时进度写入任务状态** —— 工具执行时的 `onProgress` 进度会写入任务的 `statusMessage`，客户端能看到 `"执行中 30/100"` 这样的动态信息，而不是默默等待超时。
- **LLM 输出流式化** —— 分析与规划类工具（`hy3_analyze`、`hy3_analyze_report`、`hy3_plan_chart`、`hy3_plan_dashboard`、`hy3_plan_wordcloud`、`hy3_plan_knowledge_graph`）在 Task/Stream 模式下会流式接收 Hy3 token，并把最新累积的输出写入任务的 `statusMessage`，客户端可以在最终完成前预览响应内容。

## 设计演进：从黑盒到透明、可编排的 Agentic 任务

最初的实现试图在一个同步调用里完成所有事情：

| 维度 | 之前（v0.1.x 黑盒方案） | 现在（v0.2.x 透明任务方案） |
| --- | --- | --- |
| 交互模式 | 单次 `tools/call` 一直等到 LLM 全部生成完 | 立即返回 `taskId`，客户端轮询状态并取结果 |
| 超时表现 | 默认 60 秒静默超时，直接失败 | 不再受单次调用超时限制；任务最长可运行 5 分钟 |
| 取消机制 | 客户端只能放弃等待 | `AbortSignal` 一路透传到 OpenAI SDK；`tasks/cancel` 真正中断模型请求 |
| 进度可见性 | 没有任何反馈，用户只能看转圈 | `statusMessage` 实时更新进度和部分 LLM 输出 |
| 文档分析 | `hy3_document_summary` 内部同时做提取、分析、渲染 | `hy3_extract_document` → `hy3_analyze` → Agent 保存数据 → `hy3_render_*` / `hy3_analyze_report` 工具 |
| 工具职责 | 巨型工具把读取、推理、渲染混在一起 | 每个工具职责单一，Agent 可自由组合 |
| 向后兼容 | 无任务支持 | `taskSupport: "optional"`，支持任务和不支持任务的客户端都能用 |

### 为什么更好

1. **超时不再是问题。** 立即返回 `taskId` 后，MCP 客户端不需要长时间挂起 HTTP 请求等待 Hy3 生成长报告，默认 60 秒超时不会再杀死复杂任务。
2. **用户能看到进度。** 任务执行器把增量更新（如 `"执行中 30/100"`、部分 JSON、部分报告文本）写入 `task.statusMessage`，把黑盒等待变成透明、近似流式的体验。
3. **取消真正生效。** `tasks/cancel` 产生的 `AbortSignal` 从任务执行器一路穿过各个工具，最终传入 `openai.chat.completions.create`，因此取消会真正中止正在进行的模型推理，而不是只改任务状态。
4. **Agent 可以基于中间结果继续推理。** 把 `hy3_document_summary` 拆成 `hy3_extract_document` + `hy3_analyze` 后，Agent 可以先查看原始文本，决定提取哪些结构化数据，保存为文件，再选择合适的可视化工具。Agent 不再被迫相信一个巨型工具。
5. **分析结果流式输出。** 对于分析类工具，Hy3 token 到达即消费，运行中的预览被推送到任务状态。使用 `callToolStream` 的客户端可以像 ChatGPT 一样实时看到答案被写出来。

### 设计是如何落地的

- **`McpServer`** 替代底层 `Server` 类。由 SDK 自动生成 JSON Schema、校验参数、路由请求并处理 Task/Stream 协议，服务端代码更简洁、协议更规范。
- **`server.experimental.tasks.registerToolTask`** 配合 `execution: { taskSupport: "optional" }` 把所有重工具注册为任务型工具，同时保留同步回退路径。
- **内存 `TaskStore`** + `TaskMessageQueue` 保存任务元数据和结果；TTL 清理器每 5 分钟移除已完成任务，防止内存无限增长。
- **`runToolAsTask`** 在后台运行工具、捕获异常、存储结果，并把进度/状态写入任务。流式工具通过 `onOutput` 回调实时更新任务状态。
- **`Hy3Client.chatStream`** 与 **`askHy3Stream`** 封装 OpenAI SDK 流式补全接口，并支持 `AbortSignal`。
- **Agentic 工具拆分：** `hy3_extract_document` 是纯文档解析器；`hy3_analyze` 负责文本/数据的 LLM 分析；`hy3_plan_*` 工具输出 JSON 设计方案；`hy3_render_*` 工具消费显式数据与配置，不调用 LLM。这与人类分析师的工作方式一致。

## Agentic 工作流

我们不再把所有操作塞进一个“大而全”的工具里，而是把工具拆成单一职责，让 Codex、Claude Code、Roo Code 等能力较强的 MCP 客户端自己编排调用链。

以“分析这份 PDF 报告”为例，期望的调用流程是：

```
1. hy3_extract_document(file_path="report.pdf")
   → { document_type: "pdf", text: "..." }

2. hy3_analyze(text="...", question="提取关键数据、趋势和指标")
   → JSON 格式的关键指标和趋势

3. Agent 把 JSON 保存为 report_data.csv

4. hy3_analyze_report(file_paths=["report_data.csv"], question="...")
   → 详细的 HTML/Markdown 报告

5. （可选）hy3_plan_dashboard(file_paths=["report_data.csv"])
   → Hy3 设计的 JSON 大屏方案

6. （可选）hy3_render_dashboard(file_paths=["report_data.csv"], design={...})
   → 大屏 HTML/PNG
```

每个工具只负责一件事，超时风险大幅降低；同时 Agent 可以根据用户意图灵活决定调用哪些工具。

---

## 客户端接入

### CodeBuddy / WorkBuddy

在用户目录的 `~/.codebuddy/mcp.json` 中写入：

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

运行 `hdm init` 自动配置。

### Open WebUI

Open WebUI 没有暴露可供 `hdm init` 直接写入的 stdio MCP 宿主。要在 Open WebUI 中使用 Hy3 数据分析 MCP，可以创建一个 Open WebUI [Function / Tool](https://docs.openwebui.com/features/plugin/functions/)，通过 `hy3-data-mcp` 启动子进程并代理 JSON-RPC 消息；或者单独运行服务端并通过管道转发 stdio。目前暂未提供 Open WebUI 的一键安装功能。

---

## 使用示例

### 提取文档文本

```json
{
  "name": "hy3_extract_document",
  "arguments": {
    "file_path": "./report.pdf",
    "max_text_length": 100000
  }
}
```

### 分析提取的文本

```json
{
  "name": "hy3_analyze",
  "arguments": {
    "text": "...",
    "question": "总结关键发现与风险",
    "output_format": "html",
    "language": "zh"
  }
}
```

### 分析结构化数据

```json
{
  "name": "hy3_analyze",
  "arguments": {
    "data_file_path": "./sales.csv",
    "question": "找出趋势与异常点",
    "output_format": "text",
    "language": "zh"
  }
}
```

### 规划图表

```json
{
  "name": "hy3_plan_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "question": "展示月度销售趋势",
    "chart_type_hint": "line",
    "language": "zh"
  }
}
```

### 渲染图表

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

### 堆叠柱状图

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

### 桑基图

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

### K 线图

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

### 规划词云

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

### 渲染词云

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

### 规划知识图谱

```json
{
  "name": "hy3_plan_knowledge_graph",
  "arguments": {
    "file_path": "./article.txt",
    "max_entities": 30,
    "language": "zh"
  }
}
```

### 渲染知识图谱

```json
{
  "name": "hy3_render_knowledge_graph",
  "arguments": {
    "nodes": "[{\"id\":\"A\",\"group\":1},{\"id\":\"B\",\"group\":2}]",
    "links": "[{\"source\":\"A\",\"target\":\"B\",\"relation\":\"links\"}]",
    "output_format": "png",
    "language": "zh"
  }
}
```

### 设计多文件数据大屏

```json
{
  "name": "hy3_plan_dashboard",
  "arguments": {
    "file_paths": ["./sales.csv", "./users.csv"],
    "title": "月度运营大屏",
    "layout": "grid",
    "theme": "nature",
    "language": "zh"
  }
}
```

### 渲染大屏设计

```json
{
  "name": "hy3_render_dashboard",
  "arguments": {
    "file_paths": ["./sales.csv", "./users.csv"],
    "design": {
      "title": "月度运营大屏",
      "layout": "grid",
      "charts": [
        { "file_index": 0, "chart_type": "bar", "x_column": "month", "y_column": "sales", "title": "月度销售额" }
      ]
    },
    "theme": "nature",
    "output_format": "html",
    "language": "zh"
  }
}
```

### 生成完整数据分析报告

```json
{
  "name": "hy3_analyze_report",
  "arguments": {
    "file_paths": ["./sales.csv"],
    "question": "分析销售表现并总结关键驱动因素",
    "output_format": "html",
    "max_charts": 4,
    "theme": "professional",
    "language": "zh"
  }
}
```

### 3D 柱状图

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "bar3d",
    "x_column": "month",
    "y_column": "sales",
    "output_format": "png",
    "language": "zh"
  }
}
```

### 3D 散点图

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
    "language": "zh"
  }
}
```

### 双轴组合图

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
    "language": "zh"
  }
}
```

### 使用 ECharts 配置覆盖

```json
{
  "name": "hy3_render_chart",
  "arguments": {
    "data_file_path": "./sales.csv",
    "chart_type": "bar",
    "x_column": "month",
    "y_column": "sales",
    "overrides": "{\"title\":{\"text\":\"自定义标题\"}}",
    "output_format": "svg",
    "language": "zh"
  }
}
```

---

## 输出格式说明

- **`svg`** —— 轻量、可缩放矢量图，适合嵌入报告或网页。
- **`html`** —— 基于 ECharts 的交互式页面，支持动画，可直接在浏览器打开。
- **`png`** —— 由 `sharp` 栅格化，适合 PPT、文档和社交分享。

---

## 主题与字体

所有可视化工具都支持 `theme` 参数和可选的 `font_family` 覆盖。

内置主题：

| 主题 | 风格 |
| --- | --- |
| `light` | 纯白背景，默认 ECharts 调色板。 |
| `dark` | 深色背景，高对比霓虹配色。 |
| `colorful` | 高饱和配色，适合演示。 |
| `minimal` | 低饱和、单色系友好配色。 |
| `professional` | 商务报告常用的石板灰配色。 |
| `premium` | 深海军蓝背景、精致渐变、圆角与现代专业配色。 |
| `retro` | 类似 Solarized 的暖色配色，搭配衬线字体。 |
| `science` | 绿色连续色板，搭配等宽字体。 |
| `nature` | **默认。** Nature 期刊风格，采用适合发表的 Tableau 色板与简洁排版。 |

Nature 默认主题 + 自定义字体示例：

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

### 自定义颜色

所有可视化工具还支持可选的颜色覆盖参数，方便匹配品牌色或用户偏好：

| 参数 | 说明 |
| --- | --- |
| `background_color` | 图表/页面背景色，如 `#ffffff`。 |
| `text_color` | 标题、标签、图例文字颜色，如 `#1a1a1a`。 |
| `axis_color` | 坐标轴线和刻度颜色，如 `#999999`。 |
| `split_line_color` | 网格分割线颜色，如 `#e8e8e8`。 |
| `palette` | 完整的自定义调色板，传入 HEX 颜色数组。 |
| `primary_color` | 快捷方式：替换当前主题调色板的第一个颜色。 |

自定义调色板示例：

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

## 示例数据集

`sample_data/` 目录包含简单和复杂两类演示数据，覆盖所有图表类型：

- `sample_data/complex/ecommerce_sales.csv` —— 60 行多维电商销售数据（区域、品类、渠道、收入、利润、折扣）。
- `sample_data/complex/customers.csv` —— 80 条客户记录，含人口统计、细分、LTV、流失风险。
- `sample_data/complex/marketing_campaigns.csv` —— 24 条营销活动数据，含预算、曝光、点击、转化、收入。
- `sample_data/complex/clinical_trial.csv` —— 90 条临床试验患者记录，适合科研统计分析。
- `sample_data/complex/employee_performance.csv` —— 60 条员工绩效记录，含部门、职级、薪资、满意度。
- `sample_data/complex/hierarchical_geo_sales.csv` —— 区域 → 城市 → 品类 层级数据，适合矩形树图/旭日图。
- `sample_data/complex/reviews.csv` —— 20 条真实风格的中文产品评论，适合词云与情感分析。
- `sample_data/stock.csv` —— OHLC 股票数据，适合 K 线图。
- `sample_data/report.docx` —— 一份包含季度销售报表和表格的 Word 示例文档，用于测试 `hy3_extract_document` 和 `hy3_analyze`。
- `sample_data/report.pdf` —— 同一份报表的 PDF 版本，用于测试 PDF 解析与文本分析。

运行 `node scripts/generate-sample-data.mjs` 可确定性重新生成 CSV 数据集。运行 `python scripts/generate-sample-documents.py`（需 Python 环境安装 `python-docx` 和 `fpdf2`）可重新生成 DOCX/PDF 示例。

---

## 端到端示例

分析内置的电商销售数据并生成完整 HTML 报告：

```bash
# 1. 安装并启动 MCP 服务器（见上方快速开始）
# 2. 对 sample_data/complex/ecommerce_sales.csv 调用 hy3_analyze_report
# 3. 报告会输出到 hy3-data-output/<YYYY-MM-DD>/html/data_report_<timestamp>.html
```

也可以使用 Plan → Render 流水线：

1. 对 `sample_data/complex/ecommerce_sales.csv` 调用 `hy3_plan_chart`，得到 JSON 图表方案。
2. 将方案字段传给 `hy3_render_chart`，生成 SVG/PNG/HTML 文件。
3. 用 `hy3_plan_dashboard` 设计大屏，再调用 `hy3_render_dashboard` 组合多张图表。

所有输出文件按 `hy3-data-output/<YYYY-MM-DD>/<ext>/文件名` 自动按日期和类型分目录存放。

---

## 参数速查

| 参数 | 适用工具 | 说明 |
|---|---|---|
| `data` / `data_file_path` / `file_path` | 大多数工具 | 三者提供其一即可。`data` 为 JSON 数组字符串；`data_file_path`/`file_path` 指向 CSV/JSON/XLSX。 |
| `theme` | 渲染与报告工具 | 可选 `light`、`dark`、`colorful`、`minimal`、`professional`、`premium`、`retro`、`science`、`nature`。 |
| `language` | 所有 LLM 工具 | `zh`、`en` 或 `auto`，自动根据问题或数据检测语言。 |
| `output_format` | `hy3_render_chart`、`hy3_render_wordcloud`、`hy3_render_knowledge_graph` | `svg`（默认）、`html` 或 `png`。 |
| `output_filename` | 所有输出工具 | 可选基础文件名，扩展名会自动补齐。 |
| `width` / `height` | 渲染工具与报告 | 取值范围 200–2000 像素。 |
| `chart_type` | `hy3_render_chart` | 支持 30+ 类型，所需列不同（详见错误提示）。 |

---

## 常见问题排查

**MCP 客户端长分析超时**
- `hy3_analyze`、`hy3_analyze_report` 及所有 Plan 工具均支持异步任务执行。服务器会返回 `taskId` 并流式推送进度；同步客户端会自动轮询。

**"Missing required column(s)" 报错**
- 查看错误信息中的可用列。复合图（`dual_axis`、`line_bar` 等）需提供 `value_column`；`bubble` 需提供 `size_column`；3D 图需提供 `z_column`。

**模型返回的 JSON 格式异常**
- Plan 工具已内置重试与 schema 校验。若仍解析失败，会返回兜底方案，并在结果中附带 `_warning` 字段说明情况。

**输出文件都堆在一个目录里**
- 自 v0.3.4 起，输出按 `hy3-data-output/<YYYY-MM-DD>/<ext>/文件名` 分目录存放。

**PNG 渲染失败**
- 请确保 Node.js ≥ 18，且 `@napi-rs/canvas` 已正确安装原生二进制。Windows 上通常重新 `npm install` 即可解决。

---

## 开发

```bash
git clone https://github.com/xy200303/Hy3.git
cd Hy3/hy3-data-mcp
npm install
npm run build
npm test
npm run test:coverage   # 生成覆盖率报告
npm run test:real       # 需要配置 HY3_API_KEY
```

测试套件包含 **168 条单元、集成和冒烟测试**，覆盖文档解析、工具函数、主题系统、CLI 配置、数据大屏渲染、客户端初始化、流式 LLM 输出、异步任务执行、全部可视化工具、图表渲染和 MCP Server 握手。

使用 [MCP Inspector](https://github.com/modelcontextprotocol/inspector) 调试：

```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

---

## 路线图

- [x] 11 个核心数据分析工具
- [x] SVG / HTML / PNG 三种输出格式
- [x] 命令行一键安装工具 `hdm init`
- [x] 支持 PDF、DOCX、XLSX、CSV、JSON、TXT 文档
- [x] 多种图表主题与自定义字体
- [x] 更多数据大屏布局
- [x] 长分析任务的流式进度反馈
- [x] UI 标签多语言自动检测

---

## 许可证

本项目采用 [Apache-2.0](../LICENSE) 许可证。
