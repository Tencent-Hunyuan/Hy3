import * as echarts from "echarts";
import { svgToPng } from "./png.js";
import { applyTheme, getTheme } from "./themes.js";
import type { Theme } from "./themes.js";
import type { DataTable } from "../utils.js";

export type ChartType =
  | "bar"
  | "line"
  | "area"
  | "pie"
  | "donut"
  | "rose"
  | "scatter"
  | "bubble"
  | "scatter_trend"
  | "radar"
  | "heatmap"
  | "funnel"
  | "sankey"
  | "treemap"
  | "sunburst"
  | "gauge"
  | "histogram"
  | "boxplot"
  | "candlestick"
  | "stacked_bar"
  | "grouped_bar";

export interface ChartConfig {
  x_column: string;
  y_column: string;
  title: string;
  width?: number;
  height?: number;
  value_column?: string;
  open_column?: string;
  close_column?: string;
  high_column?: string;
  low_column?: string;
  group_column?: string;
  size_column?: string;
  theme?: string;
  font_family?: string;
  background_color?: string;
  text_color?: string;
  axis_color?: string;
  split_line_color?: string;
  palette?: string[];
  primary_color?: string;
}

function themeOverridesFromConfig(config: ChartConfig): Partial<Omit<Theme, "name">> {
  const overrides: Partial<Omit<Theme, "name">> = {};
  if (config.background_color) overrides.backgroundColor = config.background_color;
  if (config.text_color) overrides.textColor = config.text_color;
  if (config.axis_color) overrides.axisColor = config.axis_color;
  if (config.split_line_color) overrides.splitLineColor = config.split_line_color;
  if (config.palette && config.palette.length > 0) {
    overrides.palette = config.palette;
  } else if (config.primary_color) {
    const base = getTheme(config.theme, config.font_family).palette;
    overrides.palette = [config.primary_color, ...base.slice(1)];
  }
  return overrides;
}

function themeOverridesToChartConfig(
  overrides?: Partial<Omit<Theme, "name">>
): Partial<ChartConfig> {
  if (!overrides) return {};
  const cfg: Partial<ChartConfig> = {};
  if (overrides.backgroundColor !== undefined) cfg.background_color = overrides.backgroundColor;
  if (overrides.textColor !== undefined) cfg.text_color = overrides.textColor;
  if (overrides.axisColor !== undefined) cfg.axis_color = overrides.axisColor;
  if (overrides.splitLineColor !== undefined) cfg.split_line_color = overrides.splitLineColor;
  if (overrides.palette !== undefined) cfg.palette = overrides.palette;
  return cfg;
}

export function renderChartSvg(
  chartType: ChartType,
  table: DataTable,
  config: ChartConfig
): string {
  const width = config.width ?? 800;
  const height = config.height ?? 500;
  const chart = echarts.init(null, null, {
    renderer: "svg",
    ssr: true,
    width,
    height,
  });

  const option = buildEChartsOption(chartType, table, config);
  chart.setOption(option);
  const svg = chart.renderToSVGString();
  chart.dispose();
  return svg;
}

export function renderChartSvgWithTheme(
  chartType: ChartType,
  table: DataTable,
  config: ChartConfig
): string {
  return renderChartSvg(chartType, table, withThemeConfig(config));
}

function withThemeConfig(config: ChartConfig): ChartConfig {
  return {
    ...config,
    theme: config.theme || "nature",
    font_family: config.font_family,
  };
}

export function renderChartHtml(
  chartType: ChartType,
  table: DataTable,
  config: ChartConfig
): string {
  const width = config.width ?? 800;
  const height = config.height ?? 500;
  const option = buildEChartsOption(chartType, table, config);
  const theme = getTheme(config.theme, config.font_family, themeOverridesFromConfig(config));
  const containerBg = theme.name === "dark" ? "#1f1f1f" : theme.backgroundColor;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(config.title)}</title>
  <style>
    body { margin: 0; padding: 24px; background: ${theme.backgroundColor}; color: ${theme.textColor}; font-family: ${theme.fontFamily}; }
    .container { max-width: ${width}px; margin: 0 auto; background: ${containerBg}; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    #chart { width: 100%; height: ${height}px; }
  </style>
</head>
<body>
  <div class="container">
    <div id="chart"></div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>
    const chart = echarts.init(document.getElementById('chart'));
    chart.setOption(${JSON.stringify(option)});
    window.addEventListener('resize', () => chart.resize());
  </script>
</body>
</html>`;
}

export function renderKnowledgeGraphSvg(
  nodes: { id: string; group: number }[],
  links: { source: string; target: string; relation: string }[],
  title: string,
  width = 900,
  height = 600,
  themeName?: string,
  fontFamily?: string,
  overrides?: Partial<Omit<Theme, "name">>
): string {
  const theme = getTheme(themeName, fontFamily, overrides);
  const chart = echarts.init(null, null, {
    renderer: "svg",
    ssr: true,
    width,
    height,
  });

  const option = buildKnowledgeGraphOption(nodes, links, title);
  chart.setOption(applyTheme(option, theme));
  const svg = chart.renderToSVGString();
  chart.dispose();
  return svg;
}

function buildKnowledgeGraphOption(
  nodes: { id: string; group: number }[],
  links: { source: string; target: string; relation: string }[],
  title: string,
  roam = false
): echarts.EChartsOption {
  return {
    title: { text: title, left: "center" },
    tooltip: {
      formatter: (params: any) => {
        if (params.dataType === "edge") {
          return `${params.data.source} → ${params.data.target}<br/>${params.data.relation}`;
        }
        return params.data.id;
      },
    },
    animationDurationUpdate: 1500,
    animationEasingUpdate: "quinticInOut",
    series: [
      {
        type: "graph",
        layout: "force",
        roam,
        label: { show: true, position: "right" },
        edgeSymbol: ["circle", "arrow"],
        edgeSymbolSize: [4, 10],
        data: nodes.map((n) => ({
          id: n.id,
          name: n.id,
          value: n.group,
          category: n.group,
          symbolSize: 24,
        })),
        links: links.map((l) => ({
          source: l.source,
          target: l.target,
          relation: l.relation,
        })),
        categories: Array.from(new Set(nodes.map((n) => n.group))).map((g) => ({
          name: String(g),
        })),
        force: {
          repulsion: 300,
          edgeLength: 100,
        },
        lineStyle: { curveness: 0.2 },
      },
    ],
  };
}

export function renderKnowledgeGraphHtml(
  nodes: { id: string; group: number }[],
  links: { source: string; target: string; relation: string }[],
  title: string,
  width = 900,
  height = 600,
  themeName?: string,
  fontFamily?: string,
  overrides?: Partial<Omit<Theme, "name">>
): string {
  const theme = getTheme(themeName, fontFamily, overrides);
  const option = applyTheme(buildKnowledgeGraphOption(nodes, links, title, true), theme);
  const containerBg = theme.name === "dark" ? "#1f1f1f" : theme.backgroundColor;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <style>
    body { margin: 0; padding: 24px; background: ${theme.backgroundColor}; color: ${theme.textColor}; font-family: ${theme.fontFamily}; }
    .container { max-width: ${width}px; margin: 0 auto; background: ${containerBg}; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    #chart { width: 100%; height: ${height}px; }
  </style>
</head>
<body>
  <div class="container">
    <div id="chart"></div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>
    const chart = echarts.init(document.getElementById('chart'));
    chart.setOption(${JSON.stringify(option)});
    window.addEventListener('resize', () => chart.resize());
  </script>
</body>
</html>`;
}

export type DashboardLayout = "grid" | "rows" | "columns" | "hero" | "compact";

export function renderDashboardHtml(
  charts: Array<{ chartType: ChartType; table: DataTable; config: ChartConfig }>,
  title: string,
  themeName?: string,
  fontFamily?: string,
  overrides?: Partial<Omit<Theme, "name">>,
  layout: DashboardLayout = "grid"
): string {
  const theme = getTheme(themeName, fontFamily, overrides);
  const cardBg = theme.name === "dark" ? "#1f1f1f" : "#ffffff";
  const chartOverrides: Partial<ChartConfig> = themeOverridesToChartConfig(overrides);

  const isHero = layout === "hero";
  const isCompact = layout === "compact";
  const isRows = layout === "rows";
  const isColumns = layout === "columns";

  const chartWidth = isCompact ? 360 : isColumns ? 520 : 500;
  const chartHeight = isCompact ? 260 : isColumns ? 360 : 350;

  const chartOptions = charts.map((c) => ({
    title: c.config.title,
    option: buildEChartsOption(c.chartType, c.table, {
      ...c.config,
      ...chartOverrides,
      theme: theme.name,
      font_family: theme.fontFamily,
      width: chartWidth,
      height: chartHeight,
    }),
  }));

  const chartDivs = chartOptions
    .map(
      (c, i) =>
        `<div class="chart-box ${isHero && i === 0 ? "chart-hero" : ""}"><h3>${escapeHtml(
          c.title
        )}</h3><div id="chart-${i}" class="chart"></div></div>`
    )
    .join("\n");

  const initScript = chartOptions
    .map(
      (c, i) => `
    (function() {
      const chart = echarts.init(document.getElementById('chart-${i}'));
      chart.setOption(${JSON.stringify(c.option)});
      window.addEventListener('resize', () => chart.resize());
    })();`
    )
    .join("\n");

  let gridStyle = "";
  if (isRows) {
    gridStyle = `grid-template-columns: 1fr;`;
  } else if (isColumns) {
    gridStyle = `grid-template-columns: repeat(${charts.length}, minmax(520px, 1fr)); overflow-x: auto;`;
  } else if (isCompact) {
    gridStyle = `grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));`;
  } else {
    gridStyle = `grid-template-columns: repeat(auto-fit, minmax(520px, 1fr));`;
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <style>
    body { font-family: ${theme.fontFamily}; margin: 0; padding: 24px; background: ${theme.backgroundColor}; color: ${theme.textColor}; }
    .container { max-width: ${isColumns ? "none" : "1200px"}; margin: 0 auto; }
    h1 { font-size: 24px; margin-bottom: 16px; }
    .grid { display: grid; ${gridStyle} gap: ${isCompact ? "16px" : "24px"}; }
    .chart-box { background: ${cardBg}; border-radius: 8px; padding: ${isCompact ? "12px" : "16px"}; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .chart-box h3 { margin: 0 0 12px 0; font-size: ${isCompact ? "14px" : "16px"}; }
    .chart { width: 100%; height: ${isCompact ? "280px" : isColumns ? "420px" : "400px"}; }
    .chart-hero { grid-column: 1 / -1; }
  </style>
</head>
<body>
  <div class="container">
    <h1>${escapeHtml(title)}</h1>
    <div class="grid">${chartDivs}</div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>${initScript}</script>
</body>
</html>`;
}

export async function renderDashboardPng(
  charts: Array<{ chartType: ChartType; table: DataTable; config: ChartConfig }>,
  title: string,
  themeName?: string,
  fontFamily?: string,
  overrides?: Partial<Omit<Theme, "name">>,
  layout: DashboardLayout = "grid"
): Promise<Buffer> {
  const theme = getTheme(themeName, fontFamily, overrides);

  const isCompact = layout === "compact";
  const isRows = layout === "rows";
  const isColumns = layout === "columns";
  const isHero = layout === "hero";

  const defaultChartWidth = isCompact ? 380 : 520;
  const defaultChartHeight = isCompact ? 280 : 380;
  const titleHeight = 60;
  const gap = isCompact ? 16 : 0;

  let cols: number;
  if (isRows) {
    cols = 1;
  } else if (isColumns) {
    cols = charts.length;
  } else if (isHero) {
    cols = 2;
  } else {
    cols = Math.min(charts.length, 2);
  }

  const rows = Math.ceil(charts.length / cols);
  const totalWidth = isHero
    ? Math.max(defaultChartWidth * 2, defaultChartWidth)
    : cols * defaultChartWidth + (cols - 1) * gap;
  const totalHeight = titleHeight + rows * defaultChartHeight + (rows - 1) * gap;
  const chartOverrides: Partial<ChartConfig> = themeOverridesToChartConfig(overrides);

  const images = charts.map((c, i) => {
    let chartWidth = defaultChartWidth;
    let chartHeight = defaultChartHeight;
    let col = i % cols;
    let row = Math.floor(i / cols);

    if (isHero) {
      if (i === 0) {
        chartWidth = totalWidth;
        chartHeight = defaultChartHeight;
        col = 0;
        row = 0;
      } else {
        chartWidth = totalWidth / 2;
        chartHeight = defaultChartHeight;
        col = (i - 1) % 2;
        row = 1 + Math.floor((i - 1) / 2);
      }
    }

    const x = col * (chartWidth + gap);
    const y = titleHeight + row * (chartHeight + gap);

    const svg = renderChartSvg(c.chartType, c.table, {
      ...c.config,
      ...chartOverrides,
      theme: theme.name,
      font_family: theme.fontFamily,
      width: Math.round(chartWidth),
      height: Math.round(chartHeight),
    });
    const base64 = Buffer.from(svg, "utf-8").toString("base64");
    return `<image x="${x}" y="${y}" width="${chartWidth}" height="${chartHeight}" href="data:image/svg+xml;base64,${base64}" preserveAspectRatio="xMidYMid meet" />`;
  });

  const dashboardSvg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${totalWidth}" height="${totalHeight}" viewBox="0 0 ${totalWidth} ${totalHeight}">
  <rect width="100%" height="100%" fill="${theme.backgroundColor}" />
  <text x="${totalWidth / 2}" y="36" font-family="${theme.fontFamily}" font-size="22" font-weight="bold" text-anchor="middle" fill="${theme.textColor}">${escapeHtml(title)}</text>
  ${images.join("\n  ")}
</svg>`;

  return svgToPng(dashboardSvg, totalWidth, totalHeight);
}

function isNumeric(value: unknown): boolean {
  return (
    typeof value === "number" ||
    (typeof value === "string" && value !== "" && !isNaN(Number(value)))
  );
}

function toNumber(value: unknown): number {
  return typeof value === "number" ? value : Number(value) || 0;
}

function linearRegression(points: { x: number; y: number }[]): {
  slope: number;
  intercept: number;
} {
  const n = points.length;
  if (n === 0) return { slope: 0, intercept: 0 };
  const sumX = points.reduce((s, p) => s + p.x, 0);
  const sumY = points.reduce((s, p) => s + p.y, 0);
  const sumXY = points.reduce((s, p) => s + p.x * p.y, 0);
  const sumXX = points.reduce((s, p) => s + p.x * p.x, 0);
  const denom = n * sumXX - sumX * sumX;
  if (denom === 0) return { slope: 0, intercept: sumY / n };
  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;
  return { slope, intercept };
}

function histogramBins(values: number[], binCount = 10): { label: string; count: number }[] {
  const clean = values.filter((v) => !isNaN(v));
  if (clean.length === 0) return [];
  const min = Math.min(...clean);
  const max = Math.max(...clean);
  if (min === max) return [{ label: String(min), count: clean.length }];
  const bins = Array.from({ length: binCount }, () => 0);
  const step = (max - min) / binCount;
  for (const v of clean) {
    const idx = Math.min(binCount - 1, Math.floor((v - min) / step));
    bins[idx]++;
  }
  return bins.map((count, i) => {
    const start = min + i * step;
    const end = min + (i + 1) * step;
    const label = `${start.toFixed(1)}-${end.toFixed(1)}`;
    return { label, count };
  });
}

function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return 0;
  if (sorted.length === 1) return sorted[0];
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  if (sorted[base + 1] !== undefined) {
    return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
  }
  return sorted[base];
}

function boxplotStats(values: number[]): [number, number, number, number, number] {
  const sorted = [...values].filter((v) => !isNaN(v)).sort((a, b) => a - b);
  if (sorted.length === 0) return [0, 0, 0, 0, 0];
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  const q1 = quantile(sorted, 0.25);
  const median = quantile(sorted, 0.5);
  const q3 = quantile(sorted, 0.75);
  return [min, q1, median, q3, max];
}

function pivotSeries(
  table: DataTable,
  xColumn: string,
  yColumn: string,
  groupColumn?: string
): {
  categories: string[];
  groups: string[];
  series: { name: string; data: number[]; stack?: string }[];
} {
  const rows = table.rows;
  const categories = Array.from(new Set(rows.map((r) => String(r[xColumn] ?? ""))));
  const groups = groupColumn
    ? Array.from(new Set(rows.map((r) => String(r[groupColumn] ?? ""))))
    : [];

  if (!groupColumn || groups.length === 0) {
    const data = categories.map((cat) => {
      const values = rows
        .filter((r) => String(r[xColumn] ?? "") === cat)
        .map((r) => toNumber(r[yColumn]));
      return values.reduce((a, b) => a + b, 0);
    });
    return { categories, groups: [yColumn], series: [{ name: yColumn, data }] };
  }

  const series = groups.map((group) => ({
    name: group,
    data: categories.map((cat) => {
      const values = rows
        .filter((r) => String(r[xColumn] ?? "") === cat && String(r[groupColumn] ?? "") === group)
        .map((r) => toNumber(r[yColumn]));
      return values.reduce((a, b) => a + b, 0);
    }),
  }));

  return { categories, groups, series };
}

function buildEChartsOption(
  chartType: ChartType,
  table: DataTable,
  config: ChartConfig
): echarts.EChartsOption {
  const option = buildEChartsOptionRaw(chartType, table, config);
  const theme = getTheme(config.theme, config.font_family, themeOverridesFromConfig(config));
  return applyTheme(option, theme);
}

function buildEChartsOptionRaw(
  chartType: ChartType,
  table: DataTable,
  config: ChartConfig
): echarts.EChartsOption {
  const xData = table.rows.map((row) => String(row[config.x_column] ?? ""));
  const yData = table.rows.map((row) => {
    const value = row[config.y_column];
    return typeof value === "number" ? value : Number(value) || 0;
  });

  const base: echarts.EChartsOption = {
    title: { text: config.title, left: "center" },
    tooltip: { trigger: "axis" },
  };

  switch (chartType) {
    case "line":
      return {
        ...base,
        xAxis: { type: "category", data: xData },
        yAxis: { type: "value" },
        series: [{ data: yData, type: "line", smooth: true }],
      };
    case "area":
      return {
        ...base,
        xAxis: { type: "category", data: xData },
        yAxis: { type: "value" },
        series: [{ data: yData, type: "line", smooth: true, areaStyle: {} }],
      };
    case "pie":
      return {
        ...base,
        tooltip: { trigger: "item" },
        series: [
          {
            type: "pie",
            radius: "50%",
            data: table.rows.map((row) => ({
              name: String(row[config.x_column] ?? ""),
              value: Number(row[config.y_column]) || 0,
            })),
          },
        ],
      };
    case "scatter":
      return {
        ...base,
        xAxis: { type: "category", data: xData },
        yAxis: { type: "value" },
        series: [{ data: yData, type: "scatter" }],
      };
    case "radar": {
      const max = Math.max(...yData, 1);
      return {
        ...base,
        radar: { indicator: xData.map((name) => ({ name, max })) },
        series: [{ type: "radar", data: [{ value: yData, name: config.y_column }] }],
      };
    }
    case "heatmap": {
      const uniqueX = Array.from(new Set(xData));
      const uniqueY = [config.y_column];
      const data = table.rows.map((_, i) => [xData[i], config.y_column, yData[i]]);
      return {
        ...base,
        xAxis: { type: "category", data: uniqueX },
        yAxis: { type: "category", data: uniqueY },
        visualMap: {
          min: Math.min(...yData),
          max: Math.max(...yData),
          calculable: true,
        },
        series: [{ type: "heatmap", data, label: { show: true } }],
      };
    }
    case "funnel":
      return {
        ...base,
        tooltip: { trigger: "item" },
        series: [
          {
            type: "funnel",
            data: table.rows.map((row) => ({
              name: String(row[config.x_column] ?? ""),
              value: Number(row[config.y_column]) || 0,
            })),
          },
        ],
      };
    case "sankey": {
      const links = table.rows.map((row) => ({
        source: String(row[config.x_column] ?? ""),
        target: String(row[config.y_column] ?? ""),
        value:
          config.value_column && row[config.value_column] !== undefined
            ? Number(row[config.value_column]) || 1
            : 1,
      }));
      const nodeNames = Array.from(new Set(links.flatMap((l) => [l.source, l.target])));
      const nodes = nodeNames.map((name) => ({ name }));
      return {
        ...base,
        tooltip: { trigger: "item", triggerOn: "mousemove" },
        series: [
          {
            type: "sankey",
            data: nodes,
            links,
            emphasis: { focus: "adjacency" },
            lineStyle: { curveness: 0.5 },
          },
        ],
      };
    }
    case "treemap":
      return {
        ...base,
        tooltip: { trigger: "item" },
        series: [
          {
            type: "treemap",
            data: table.rows.map((row) => ({
              name: String(row[config.x_column] ?? ""),
              value: Number(row[config.y_column]) || 0,
            })),
          },
        ],
      };
    case "sunburst":
      return {
        ...base,
        tooltip: { trigger: "item" },
        series: [
          {
            type: "sunburst",
            data: table.rows.map((row) => ({
              name: String(row[config.x_column] ?? ""),
              value: Number(row[config.y_column]) || 0,
            })),
            radius: [0, "90%"],
          },
        ],
      };
    case "gauge": {
      const avg = yData.length ? yData.reduce((a, b) => a + b, 0) / yData.length : 0;
      return {
        ...base,
        series: [
          {
            type: "gauge",
            detail: { formatter: "{value}" },
            data: [{ value: Math.round(avg * 100) / 100, name: config.x_column || config.title }],
          },
        ],
      };
    }
    case "boxplot": {
      const groups = new Map<string, number[]>();
      for (const row of table.rows) {
        const key = String(row[config.x_column] ?? "");
        const value = Number(row[config.y_column]) || 0;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key)!.push(value);
      }
      const categories = Array.from(groups.keys());
      const data = categories.map((cat) => boxplotStats(groups.get(cat)!));
      return {
        ...base,
        xAxis: { type: "category", data: categories },
        yAxis: { type: "value" },
        series: [{ type: "boxplot", data, itemStyle: { borderWidth: 1 } }],
      };
    }
    case "candlestick": {
      const open = config.open_column || "open";
      const close = config.close_column || "close";
      const low = config.low_column || "low";
      const high = config.high_column || "high";
      const source = [
        [config.x_column, open, close, low, high],
        ...table.rows.map((row) => [
          String(row[config.x_column] ?? ""),
          Number(row[open]) || 0,
          Number(row[close]) || 0,
          Number(row[low]) || 0,
          Number(row[high]) || 0,
        ]),
      ];
      return {
        ...base,
        tooltip: { trigger: "axis" },
        xAxis: {
          type: "category",
          data: table.rows.map((row) => String(row[config.x_column] ?? "")),
        },
        yAxis: { type: "value", scale: true },
        series: [
          {
            type: "candlestick",
            encode: { x: config.x_column, y: [open, close, low, high] },
            data: source.slice(1),
          },
        ],
      };
    }
    case "donut":
      return {
        ...base,
        tooltip: { trigger: "item" },
        series: [
          {
            type: "pie",
            radius: ["40%", "70%"],
            data: table.rows.map((row) => ({
              name: String(row[config.x_column] ?? ""),
              value: Number(row[config.y_column]) || 0,
            })),
          },
        ],
      };
    case "rose":
      return {
        ...base,
        tooltip: { trigger: "item" },
        series: [
          {
            type: "pie",
            radius: [20, 100],
            roseType: "area",
            data: table.rows.map((row) => ({
              name: String(row[config.x_column] ?? ""),
              value: Number(row[config.y_column]) || 0,
            })),
          },
        ],
      };
    case "bubble": {
      const sizeColumn = config.size_column || config.y_column;
      const sizeData = table.rows.map((row) => toNumber(row[sizeColumn]));
      const maxSize = Math.max(...sizeData, 1);
      const xIsNumeric = table.rows.every((row) => isNumeric(row[config.x_column]));
      const data = table.rows.map((row, i) => [
        xIsNumeric ? toNumber(row[config.x_column]) : i,
        toNumber(row[config.y_column]),
        sizeData[i],
      ]);
      return {
        ...base,
        tooltip: {
          trigger: "item",
          formatter: (params: any) => {
            return `${config.x_column}: ${params.data[0]}<br/>${config.y_column}: ${params.data[1]}<br/>${sizeColumn}: ${params.data[2]}`;
          },
        },
        xAxis: { type: xIsNumeric ? "value" : "category", data: xIsNumeric ? undefined : xData },
        yAxis: { type: "value" },
        series: [
          {
            type: "scatter",
            data,
            symbolSize: (d: any) => 8 + (d[2] / maxSize) * 50,
          },
        ],
      };
    }
    case "scatter_trend": {
      const xIsNumeric = table.rows.every((row) => isNumeric(row[config.x_column]));
      const points = table.rows.map((row, i) => ({
        x: xIsNumeric ? toNumber(row[config.x_column]) : i,
        y: toNumber(row[config.y_column]),
      }));
      const { slope, intercept } = linearRegression(points);
      const minX = Math.min(...points.map((p) => p.x));
      const maxX = Math.max(...points.map((p) => p.x));
      const trendLine = [
        [minX, slope * minX + intercept],
        [maxX, slope * maxX + intercept],
      ];
      return {
        ...base,
        tooltip: { trigger: "axis" },
        xAxis: { type: xIsNumeric ? "value" : "category", data: xIsNumeric ? undefined : xData },
        yAxis: { type: "value" },
        series: [
          {
            type: "scatter",
            data: points.map((p) => [p.x, p.y]),
          },
          {
            type: "line",
            data: trendLine,
            smooth: false,
            symbol: "none",
            lineStyle: { type: "dashed", width: 2 },
          },
        ],
      };
    }
    case "histogram": {
      const numericColumn = table.rows.every((row) => isNumeric(row[config.x_column]))
        ? config.x_column
        : config.y_column;
      const values = table.rows.map((row) => toNumber(row[numericColumn]));
      const bins = histogramBins(values, 12);
      return {
        ...base,
        xAxis: { type: "category", data: bins.map((b) => b.label) },
        yAxis: { type: "value" },
        series: [{ data: bins.map((b) => b.count), type: "bar" }],
      };
    }
    case "stacked_bar":
    case "grouped_bar": {
      const { categories, series } = pivotSeries(
        table,
        config.x_column,
        config.y_column,
        config.group_column
      );
      const isStacked = chartType === "stacked_bar";
      return {
        ...base,
        xAxis: { type: "category", data: categories },
        yAxis: { type: "value" },
        series: series.map((s) => ({
          name: s.name,
          type: "bar",
          data: s.data,
          ...(isStacked ? { stack: "total" } : {}),
        })),
      };
    }
    case "bar":
    default:
      return {
        ...base,
        xAxis: { type: "category", data: xData },
        yAxis: { type: "value" },
        series: [{ data: yData, type: "bar" }],
      };
  }
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
