## 关联 Issue

Closes [Tencent-Hunyuan/Hy3#3](https://github.com/Tencent-Hunyuan/Hy3/issues/3)

## 项目简介

**Hy3 Data MCP**（`hy3-data-mcp`）是一个基于 [Model Context Protocol](https://modelcontextprotocol.io) 的本地 stdio MCP Server。它调用 **腾讯混元 Hy3** API，把 CSV / JSON / Excel / PDF / Word / 文本等数据转换成图表、数据大屏、词云、知识图谱和分析报告。

输出格式支持 **SVG**、**HTML**、**PNG**，并内置 `hdm init` 命令行安装器，可一键配置 CodeBuddy、Cursor、Cline、Roo Code、Continue、Codex CLI、OpenCode 等客户端。

## 核心功能

- **11 个 MCP 工具**，按 **Extract → Analyze → Plan → Render** 四阶段拆分
- **文档解析**：PDF、DOCX、TXT、CSV、JSON、XLSX，支持表格提取
- **数据分析**：Hy3 驱动的文本 / 数据分析、完整 HTML / Markdown 报告
- **图表规划与渲染**：30+ 图表类型，包括 3D、K-line、桑基、小提琴、双轴组合等
- **数据大屏**：多图表仪表盘，支持 KPI 卡片与主题切换
- **词云 & 知识图谱**：从文本抽取关键词 / 实体关系并渲染
- **异步任务**：MCP Task / Stream，支持进度上报、流式输出、真实取消
- **多主题 & 自定义颜色**：light / dark / professional / nature 等 9 套主题

## 安装与验证

```bash
npm install -g ./releases/hy3-data-mcp-0.3.11.tgz
hy3-data-mcp
hdm init
```

验证结果：

- `npm test`：**174 / 174** 通过
- `npm audit`：**0** 漏洞

## 演示视频

<video src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/demo.mp4" controls width="100%"></video>

## 效果图展示

<table>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/01-stacked-bar.png" width="420" alt="堆叠柱状图"><br/>堆叠柱状图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/02-bubble.png" width="420" alt="气泡图"><br/>气泡图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/03-boxplot.png" width="420" alt="箱线图"><br/>箱线图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/04-candlestick.png" width="420" alt="K 线图"><br/>K 线图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/05-funnel.png" width="420" alt="漏斗图"><br/>漏斗图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/06-sunburst.png" width="420" alt="旭日图"><br/>旭日图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/07-radar.png" width="420" alt="雷达图"><br/>雷达图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/08-wordcloud.png" width="420" alt="词云"><br/>词云</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/09-knowledge-graph.png" width="420" alt="知识图谱"><br/>知识图谱</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/10-dashboard.png" width="420" alt="单仪表盘"><br/>单仪表盘</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/11-bar3d.png" width="420" alt="3D 柱状图"><br/>3D 柱状图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/12-scatter3d.png" width="420" alt="3D 散点图"><br/>3D 散点图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/13-line3d.png" width="420" alt="3D 折线图"><br/>3D 折线图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/14-line_bar.png" width="420" alt="折线+柱状组合"><br/>折线 + 柱状组合</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/15-dual_axis.png" width="420" alt="双轴组合"><br/>双轴组合</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/16-stacked_area.png" width="420" alt="堆叠面积图"><br/>堆叠面积图</td>
  </tr>
  <tr>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/17-grouped_line.png" width="420" alt="分组折线图"><br/>分组折线图</td>
    <td align="center"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/screenshots/18-area_bar.png" width="420" alt="面积+柱状组合"><br/>面积 + 柱状组合</td>
  </tr>
  <tr>
    <td align="center" colspan="2"><img src="https://raw.githubusercontent.com/xy200303/Hy3/feat/add-hy3-data-mcp/hy3-data-mcp/assets/dashboard_2024_Sales___Profit_Dashboard_1783662671334.png" width="860" alt="2024 Sales & Profit Dashboard"><br/>2024 Sales &amp; Profit Dashboard（PNG 合成大屏）</td>
  </tr>
</table>

## RhinoBird 2026 提交清单

- [x] 基于 Hy3 的 MCP Server
- [x] 至少 3 个 tool
- [x] 外部数据源 / 工具
- [x] 本地 stdio 模式
- [x] 不硬编码 API Key
- [x] 在 2+ 个 MCP 客户端验证
- [x] 一键安装包
- [x] 完整 README、演示视频与效果图
