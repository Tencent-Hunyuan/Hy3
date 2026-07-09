# Hy3 数据分析 MCP

[![License](https://img.shields.io/badge/License-Apache%202.0-blue)](#license)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-blue?logo=typescript)](#)
[![MCP](https://img.shields.io/badge/MCP-1.0+-green)](#)
[![Hy3](https://img.shields.io/badge/Powered%20by-Hy3-orange)](#)

> 让任意 CSV、JSON、Excel、PDF、Word 或文本文件，通过 **腾讯混元 Hy3** 驱动的 MCP 服务器，一键变成图表、数据大屏、词云、知识图谱和 AI 洞察。

**Hy3 数据分析 MCP** 是一个基于 [Model Context Protocol](https://modelcontextprotocol.io) 的服务端，它让你的 AI 助手拥有数据分析能力：你用自然语言提问，Hy3 完成推理，服务端渲染出可用于报告、网页或演示的 **SVG**、**HTML** 或 **PNG** 可视化结果。

![Demo](./assets/demo.gif)

本项目为 **2026 腾讯犀牛鸟开源人才培养活动** issue [Build an MCP Server powered by Hy3](https://github.com/Tencent-Hunyuan/Hy3/issues/3) 而开发。

---

## 为什么选择 Hy3 数据分析 MCP？

- **对话即可视化** —— 在 MCP 客户端里一句话就能生成图表、词云、知识图谱或数据大屏。
- **Hy3 负责思考** —— 字段选择、标题生成、关键词抽取、实体关系识别、大屏布局都交给 Hy3 模型完成。
- **多种输出格式** —— SVG 适合嵌入文档，HTML 可交互浏览，PNG 可直接放入 PPT 或社交媒体分享。
- **隐私优先** —— API Key 仅保存在本地 `.env` 文件中，代码中不硬编码任何密钥，也不会把数据发送到其他第三方服务。
- **兼容主流客户端** —— 支持 CodeBuddy、WorkBuddy、Cline、Cursor、Roo Code、Continue、Codex CLI、OpenCode 等任意 stdio MCP 客户端。

---

## 功能特性

| 工具 | 功能 | 输出格式 |
| --- | --- | --- |
| `hy3_data_visualize` | 读取结构化数据，生成柱状图、折线图、面积图、饼图、环形图、玫瑰图、散点图、气泡图、带趋势线的散点图、雷达图、热力图、漏斗图、桑基图、矩形树图、旭日图、仪表盘、直方图、箱线图、K 线图、堆叠柱状图和分组柱状图。 | `svg` / `html` / `png` |
| `hy3_wordcloud` | 由 Hy3 提取关键词及权重，渲染词云。 | `svg` / `html` / `png` |
| `hy3_knowledge_graph` | 由 Hy3 抽取实体与关系，渲染力导向知识图谱。 | `svg` / `html` / `png` |
| `hy3_data_dashboard` | 综合多个数据文件，由 Hy3 设计布局生成多图数据大屏。 | `html` / `png` |
| `hy3_data_insight` | 对数据进行分析，返回趋势、异常点等文字洞察。 | `text` |
| `hy3_document_summary` | 总结或问答 PDF、DOCX、TXT、CSV、JSON、XLSX 文档。 | `text` / `html` |
| `hy3_document_visualize` | 从文档中提取结构化数据并生成图表或大屏。 | `svg` / `html` / `png` |

---

## 快速开始

### 1. 获取 API Key

前往 [TokenHub](https://tokenhub.tencentmaas.com) 注册并创建 Hy3 模型的 API Key。

### 2. 使用 `npx` 免安装运行

```bash
cp .env.example .env
# 编辑 .env，填入 HY3_API_KEY
npx -y hy3-data-mcp
```

### 3. 或全局安装

```bash
npm install -g hy3-data-mcp
hy3-data-mcp
```

### 4. 一键配置客户端

```bash
npx -y hy3-data-mcp hdm init
```

`hdm init` 会扫描系统中的 MCP 客户端、让你选择目标客户端，并自动写入配置和 `.env` 文件。

---

## 配置说明

在项目根目录创建 `.env` 文件：

```dotenv
HY3_API_KEY=your-tokenhub-api-key
HY3_BASE_URL=https://tokenhub.tencentmaas.com/v1
HY3_MODEL=hy3-preview
HY3_OUTPUT_DIR=./hy3-mcp-output
```

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `HY3_API_KEY` | 是 | — | TokenHub / Hy3 API Key。 |
| `HY3_BASE_URL` | 否 | `https://tokenhub.tencentmaas.com/v1` | OpenAI 兼容接口地址。 |
| `HY3_MODEL` | 否 | `hy3-preview` | 模型名。 |
| `HY3_OUTPUT_DIR` | 否 | `./hy3-mcp-output` | 生成文件的输出目录。 |

---

## 客户端接入

### CodeBuddy / WorkBuddy

在项目目录的 `.codebuddy/mcp.json` 中写入：

```json
{
  "mcpServers": {
    "hy3-data-mcp": {
      "command": "npx",
      "args": ["-y", "hy3-data-mcp"],
      "env": {
        "HY3_API_KEY": "your-tokenhub-api-key",
        "HY3_BASE_URL": "https://tokenhub.tencentmaas.com/v1",
        "HY3_MODEL": "hy3-preview",
        "HY3_OUTPUT_DIR": "./hy3-mcp-output"
      }
    }
  }
}
```

### Cline / Cursor / Roo Code / Continue

运行 `hdm init` 自动配置，或从 [`configs/`](./configs/) 复制对应配置片段。

---

## 使用示例

### CSV 分析与可视化

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

### 桑基图

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

### 科研箱线图

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

### 气泡图

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

### 堆叠柱状图

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

### 直方图

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

### K 线图

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

### 多文件数据大屏

```json
{
  "name": "hy3_data_dashboard",
  "arguments": {
    "file_paths": ["./sales.csv", "./users.csv"],
    "title": "月度运营大屏",
    "theme": "nature",
    "output_format": "html",
    "language": "zh"
  }
}
```

### 文本词云

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

### 文档总结

```json
{
  "name": "hy3_document_summary",
  "arguments": {
    "file_path": "./report.pdf",
    "question": "总结关键发现与风险",
    "output_format": "html",
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
| `retro` | 类似 Solarized 的暖色配色，搭配衬线字体。 |
| `science` | 绿色连续色板，搭配等宽字体。 |
| `nature` | **默认。** Nature 期刊风格，采用适合发表的 Tableau 色板与简洁排版。 |

Nature 默认主题 + 自定义字体示例：

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

运行 `node scripts/generate-sample-data.mjs` 可确定性重新生成这些数据集。

---

## 开发

```bash
git clone https://github.com/Tencent-Hunyuan/Hy3.git
cd Hy3/hy3-data-mcp
npm install
npm run build
npm test
npm run test:real   # 需要配置 HY3_API_KEY
```

使用 [MCP Inspector](https://github.com/modelcontextprotocol/inspector) 调试：

```bash
npx @modelcontextprotocol/inspector node dist/index.js
```

---

## 路线图

- [x] 7 个核心数据分析工具
- [x] SVG / HTML / PNG 三种输出格式
- [x] 命令行一键安装工具 `hdm init`
- [x] 支持 PDF、DOCX、XLSX、CSV、JSON、TXT 文档
- [x] 多种图表主题与自定义字体
- [ ] 更多数据大屏布局
- [ ] 长分析任务的流式进度反馈
- [ ] 长分析任务的流式进度反馈
- [ ] UI 标签多语言自动检测

---

## 许可证

本项目采用 [Apache-2.0](../LICENSE) 许可证。
