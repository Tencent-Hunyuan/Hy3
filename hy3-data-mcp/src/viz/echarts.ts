import * as echarts from "echarts";
import { is3dChartType, render3dSvg, render3dWebGlHtml } from "./3d.js";
import { svgToPng } from "./png.js";
import { applyTheme, echartsThemeObject, getTheme, themes } from "./themes.js";
import type { Theme } from "./themes.js";
import type { DataTable } from "../utils.js";
export type { DataTable } from "../utils.js";

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
  | "grouped_bar"
  // pseudo-3D charts rendered as SVG isometric projections
  | "bar3d"
  | "scatter3d"
  | "line3d"
  // composite charts
  | "line_bar"
  | "area_bar"
  | "dual_axis"
  | "stacked_area"
  | "grouped_line"
  // statistical charts rendered as custom SVG
  | "violin"
  | "errorbar";

export interface ChartConfig {
  x_column: string;
  y_column: string;
  title: string;
  subtitle?: string;
  width?: number;
  height?: number;
  value_column?: string;
  open_column?: string;
  close_column?: string;
  high_column?: string;
  low_column?: string;
  group_column?: string;
  size_column?: string;
  z_column?: string;
  lower_column?: string;
  upper_column?: string;
  theme?: string;
  font_family?: string;
  background_color?: string;
  text_color?: string;
  axis_color?: string;
  split_line_color?: string;
  palette?: string[];
  primary_color?: string;
  legend_position?: "top" | "bottom" | "left" | "right";
  show_grid?: boolean;
  show_tooltip?: boolean;
  x_name?: string;
  y_name?: string;
  x_label_rotate?: number;
  line_smooth?: boolean;
  line_symbol?: "circle" | "rect" | "triangle" | "diamond" | "pin" | "arrow" | "none";
  line_area?: boolean;
  bar_stack?: boolean;
  mark_point?: boolean;
  mark_line?: boolean;
  data_zoom?: boolean;
  overrides?: string;
  show_data_table?: boolean;
  enable_theme_switcher?: boolean;
  interactive_3d?: boolean;
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
  if (is3dChartType(chartType)) {
    return render3dSvg(chartType, table, config);
  }

  if (chartType === "violin" || chartType === "errorbar") {
    const theme = getTheme(config.theme, config.font_family, themeOverridesFromConfig(config));
    const width = config.width ?? 800;
    const height = config.height ?? 500;
    return chartType === "violin"
      ? violinSvg(table, config, theme, width, height)
      : errorbarSvg(table, config, theme, width, height);
  }

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

  if (is3dChartType(chartType)) {
    const theme = getTheme(config.theme, config.font_family, themeOverridesFromConfig(config));
    if (config.interactive_3d) {
      return render3dWebGlHtml(chartType as any, table, config);
    }
    const svg = render3dSvg(chartType, table, config);
    return wrapStaticSvgHtml(svg, config.title, theme);
  }

  if (chartType === "violin" || chartType === "errorbar") {
    const theme = getTheme(config.theme, config.font_family, themeOverridesFromConfig(config));
    const width = config.width ?? 800;
    const height = config.height ?? 500;
    const svg =
      chartType === "violin"
        ? violinSvg(table, config, theme, width, height)
        : errorbarSvg(table, config, theme, width, height);
    return wrapStaticSvgHtml(svg, config.title, theme);
  }

  const option = buildEChartsOptionForHtml(chartType, table, config);
  const theme = getTheme(config.theme, config.font_family, themeOverridesFromConfig(config));
  const containerBg = theme.name === "dark" ? "#1f1f1f" : theme.name === "premium" ? "#0F172A" : theme.backgroundColor;
  const themeObjects = Object.fromEntries(
    Object.entries(themes).map(([name, t]) => [name, echartsThemeObject(t)])
  );
  const switcher = config.enable_theme_switcher
    ? `<div style="text-align:right;margin-bottom:8px">
      <label style="font-size:13px;color:${theme.textColor}">Theme
        <select id="themeSwitcher" style="margin-left:6px;padding:4px 8px;border-radius:6px;border:1px solid ${theme.axisColor};background:${containerBg};color:${theme.textColor}">
          ${Object.keys(themes)
            .map((n) => `<option value="${n}"${n === theme.name ? " selected" : ""}>${n}</option>`)
            .join("")}
        </select>
      </label>
    </div>`
    : "";
  const switcherScript = config.enable_theme_switcher
    ? `
    const themeObjects = ${JSON.stringify(themeObjects)};
    Object.entries(themeObjects).forEach(([name, t]) => echarts.registerTheme(name, t));
    const switcher = document.getElementById('themeSwitcher');
    switcher.addEventListener('change', (e) => {
      const name = e.target.value;
      const t = themeObjects[name];
      window.__hy3Chart.dispose();
      window.__hy3Chart = echarts.init(document.getElementById('chart'), name);
      window.__hy3Chart.setOption(option);
      document.body.style.background = t.backgroundColor;
      document.body.style.color = t.textStyle.color;
      const container = document.querySelector('.container');
      container.style.background = name === 'dark' ? '#1f1f1f' : name === 'premium' ? '#0F172A' : t.backgroundColor;
      container.style.color = t.textStyle.color;
      switcher.style.background = container.style.background;
      switcher.style.color = t.textStyle.color;
    });`
    : "";
  const initTheme = config.enable_theme_switcher ? theme.name : null;

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
    ${switcher}
    <div id="chart"></div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>
    const option = ${JSON.stringify(option)};
    window.__hy3Chart = echarts.init(document.getElementById('chart')${initTheme ? `, '${initTheme}'` : ""});
    window.__hy3Chart.setOption(option);
    window.addEventListener('resize', () => window.__hy3Chart.resize());
    ${switcherScript}
  </script>
  ${config.show_data_table ? renderDataTableHtml(table, theme) : ""}
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
  const containerBg = theme.name === "dark" ? "#1f1f1f" : theme.name === "premium" ? "#0F172A" : theme.backgroundColor;

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
  layout: DashboardLayout = "grid",
  showKpi = true,
  language: "zh" | "en" = "en",
  enableThemeSwitcher = false
): string {
  const theme = getTheme(themeName, fontFamily, overrides);
  const cardBg = theme.name === "dark" ? "#1f1f1f" : theme.name === "premium" ? "#0F172A" : "#ffffff";
  const chartOverrides: Partial<ChartConfig> = themeOverridesToChartConfig(overrides);

  const isHero = layout === "hero";
  const isCompact = layout === "compact";
  const isRows = layout === "rows";
  const isColumns = layout === "columns";

  const chartWidth = isCompact ? 360 : isColumns ? 520 : 500;
  const chartHeight = isCompact ? 260 : isColumns ? 360 : 350;

  const chartItems = charts.map((c) => {
    const config = {
      ...c.config,
      ...chartOverrides,
      theme: theme.name,
      font_family: theme.fontFamily,
      width: chartWidth,
      height: chartHeight,
    };
    if (is3dChartType(c.chartType)) {
      return { title: c.config.title, svg: renderChartSvg(c.chartType, c.table, config) };
    }
    const option = enableThemeSwitcher
      ? buildEChartsOptionForHtml(c.chartType, c.table, config)
      : buildEChartsOption(c.chartType, c.table, config);
    return { title: c.config.title, option };
  });

  const kpiCards = showKpi ? buildKpiCards(charts, theme, cardBg, language) : "";

  const chartDivs = chartItems
    .map((c, i) => {
      const heroClass = isHero && i === 0 ? "chart-hero" : "";
      const inner = "svg" in c && c.svg
        ? `<img src="data:image/svg+xml;base64,${Buffer.from(c.svg, "utf-8").toString("base64")}" alt="${escapeHtml(c.title)}" style="width:100%;height:100%;" />`
        : `<div id="chart-${i}" class="chart"></div>`;
      return `<div class="chart-box ${heroClass}"><h3>${escapeHtml(c.title)}</h3>${inner}</div>`;
    })
    .join("\n");

  const themeObjects = Object.fromEntries(
    Object.entries(themes).map(([name, t]) => [name, echartsThemeObject(t)])
  );
  const initTheme = enableThemeSwitcher ? theme.name : null;
  const chartRefs = chartItems
    .map((c, i) => ("option" in c ? { id: `chart-${i}`, option: c.option } : null))
    .filter(Boolean) as Array<{ id: string; option: any }>;

  const initScript = chartRefs
    .map(
      (ref) => `
    (function() {
      const chart = echarts.init(document.getElementById('${ref.id}')${initTheme ? `, '${initTheme}'` : ""});
      chart.setOption(${JSON.stringify(ref.option)});
      window.__hy3Charts = window.__hy3Charts || [];
      window.__hy3Charts.push({ id: '${ref.id}', option: ${JSON.stringify(ref.option)} });
      window.addEventListener('resize', () => chart.resize());
    })();`
    )
    .join("\n");

  const switcherHtml = enableThemeSwitcher
    ? `<div style="text-align:right;margin-bottom:16px">
      <label style="font-size:14px;color:${theme.textColor}">Theme
        <select id="dashboardThemeSwitcher" style="margin-left:8px;padding:6px 10px;border-radius:6px;border:1px solid ${theme.axisColor};background:${cardBg};color:${theme.textColor}">
          ${Object.keys(themes)
            .map((n) => `<option value="${n}"${n === theme.name ? " selected" : ""}>${n}</option>`)
            .join("")}
        </select>
      </label>
    </div>`
    : "";

  const switcherScript = enableThemeSwitcher
    ? `
    const themeObjects = ${JSON.stringify(themeObjects)};
    Object.entries(themeObjects).forEach(([name, t]) => echarts.registerTheme(name, t));
    const picker = (name) => name === 'dark' ? '#1f1f1f' : name === 'premium' ? '#0F172A' : '#ffffff';
    document.getElementById('dashboardThemeSwitcher').addEventListener('change', (e) => {
      const name = e.target.value;
      const t = themeObjects[name];
      window.__hy3Charts.forEach((ref) => {
        echarts.dispose(document.getElementById(ref.id));
        const newChart = echarts.init(document.getElementById(ref.id), name);
        newChart.setOption(ref.option);
      });
      document.body.style.background = t.backgroundColor;
      document.body.style.color = t.textStyle.color;
      document.querySelectorAll('.chart-box, .kpi-card').forEach((el) => {
        el.style.background = picker(name);
        el.style.color = t.textStyle.color;
      });
      e.target.style.background = picker(name);
      e.target.style.color = t.textStyle.color;
    });`
    : "";


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
    .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .kpi-card { background: ${cardBg}; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }
    .kpi-label { font-size: 13px; opacity: 0.8; margin-bottom: 6px; }
    .kpi-value { font-size: 22px; font-weight: bold; }
  </style>
</head>
<body>
  <div class="container">
    <h1>${escapeHtml(title)}</h1>
    ${switcherHtml}
    ${kpiCards}
    <div class="grid">${chartDivs}</div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script>${initScript}${switcherScript}</script>
</body>
</html>`;
}

function buildKpiCards(
  charts: Array<{ chartType: ChartType; table: DataTable; config: ChartConfig }>,
  theme: Theme,
  cardBg: string,
  language: "zh" | "en"
): string {
  if (charts.length === 0) return "";
  const first = charts[0];
  const yCol = first.config.y_column;
  const numericValues = first.table.rows
    .map((row) => Number(row[yCol]))
    .filter((v) => Number.isFinite(v));
  if (numericValues.length === 0) return "";

  const total = numericValues.reduce((a, b) => a + b, 0);
  const avg = total / numericValues.length;
  const max = Math.max(...numericValues);
  const min = Math.min(...numericValues);

  const fmt = (n: number) => n.toLocaleString(language === "zh" ? "zh-CN" : "en-US");
  const labels =
    language === "zh"
      ? [`总计 ${yCol}`, `平均 ${yCol}`, `最大 ${yCol}`, `最小 ${yCol}`]
      : [`Total ${yCol}`, `Avg ${yCol}`, `Max ${yCol}`, `Min ${yCol}`];
  const values = [fmt(total), fmt(Number(avg.toFixed(2))), fmt(max), fmt(min)];

  const cards = labels
    .map(
      (label, i) => `
    <div class="kpi-card" style="background:${cardBg};color:${theme.textColor};font-family:${theme.fontFamily};">
      <div class="kpi-label">${escapeHtml(label)}</div>
      <div class="kpi-value">${escapeHtml(values[i])}</div>
    </div>`
    )
    .join("");

  return `<div class="kpi-row">${cards}</div>`;
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
  let themed = applyTheme(option, theme);
  if (theme.name === "premium" || theme.name === "professional") {
    applyPremiumStyling(themed, theme);
  }
  themed = applyChartConfigOverrides(themed, config);
  if (config.overrides) {
    const parsed = parseOverrides(config.overrides);
    if (parsed) {
      themed = deepMerge(themed, parsed) as echarts.EChartsOption;
    }
  }
  return themed;
}

function buildEChartsOptionForHtml(
  chartType: ChartType,
  table: DataTable,
  config: ChartConfig
): echarts.EChartsOption {
  let option = buildEChartsOptionRaw(chartType, table, config);
  option = applyChartConfigOverrides(option, config);
  if (config.overrides) {
    const parsed = parseOverrides(config.overrides);
    if (parsed) {
      option = deepMerge(option, parsed) as echarts.EChartsOption;
    }
  }
  return option;
}

function parseOverrides(overrides: string): unknown {
  try {
    return JSON.parse(overrides);
  } catch {
    return null;
  }
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function deepMerge(target: unknown, source: unknown): unknown {
  if (isPlainObject(target) && isPlainObject(source)) {
    const result: Record<string, unknown> = { ...target };
    for (const key of Object.keys(source)) {
      const sourceValue = source[key];
      const targetValue = result[key];
      if (isPlainObject(sourceValue) && isPlainObject(targetValue)) {
        result[key] = deepMerge(targetValue, sourceValue);
      } else {
        result[key] = sourceValue;
      }
    }
    return result;
  }
  return source;
}

function applyChartConfigOverrides(
  option: echarts.EChartsOption,
  config: ChartConfig
): echarts.EChartsOption {
  const opt = { ...option } as Record<string, unknown>;

  const title = (opt.title as Record<string, unknown>) || {};
  opt.title = { ...title, left: "center", top: 8 };

  if (config.subtitle) {
    opt.title = { ...(opt.title as Record<string, unknown>), subtext: config.subtitle };
  }

  const legend = (opt.legend as Record<string, unknown>) || {};
  const hasLegendVerticalPos =
    legend.top !== undefined ||
    legend.bottom !== undefined ||
    legend.left !== undefined ||
    legend.right !== undefined;

  if (config.legend_position === "top" || (!config.legend_position && !hasLegendVerticalPos)) {
    const legendTop = config.subtitle ? 52 : 36;
    opt.legend = { ...legend, top: legendTop };
  } else if (config.legend_position) {
    const positions: Record<string, Record<string, unknown>> = {
      bottom: { bottom: 0 },
      left: { left: 0, orient: "vertical" },
      right: { right: 0, orient: "vertical" },
    };
    opt.legend = { ...legend, ...positions[config.legend_position] };
  }

  if ((opt.legend as Record<string, unknown>)?.top !== undefined) {
    const grid = (opt.grid as Record<string, unknown>) || {};
    if (grid.top === undefined) {
      opt.grid = { ...grid, top: 90, containLabel: true };
    }
  }

  if (config.show_grid === false) {
    if (opt.xAxis && isPlainObject(opt.xAxis)) {
      opt.xAxis = { ...(opt.xAxis as Record<string, unknown>), splitLine: { show: false } };
    }
    if (opt.yAxis && isPlainObject(opt.yAxis)) {
      opt.yAxis = { ...(opt.yAxis as Record<string, unknown>), splitLine: { show: false } };
    }
  }

  if (config.show_tooltip === false) {
    opt.tooltip = { show: false };
  }

  if (config.x_name && opt.xAxis && isPlainObject(opt.xAxis)) {
    opt.xAxis = { ...(opt.xAxis as Record<string, unknown>), name: config.x_name };
  }

  if (config.y_name && opt.yAxis && isPlainObject(opt.yAxis)) {
    opt.yAxis = { ...(opt.yAxis as Record<string, unknown>), name: config.y_name };
  }

  if (config.x_label_rotate !== undefined && opt.xAxis && isPlainObject(opt.xAxis)) {
    const axis = opt.xAxis as Record<string, unknown>;
    opt.xAxis = {
      ...axis,
      axisLabel: { ...(axis.axisLabel as Record<string, unknown>), rotate: config.x_label_rotate },
    };
  }

  if (config.data_zoom && opt.xAxis) {
    opt.dataZoom = [{ type: "inside" }, { type: "slider" }];
  }

  if (opt.series && Array.isArray(opt.series)) {
    opt.series = opt.series.map((series: any) => {
      if (!series) return series;
      const s = { ...series };

      if (s.type === "line") {
        if (config.line_smooth !== undefined) s.smooth = config.line_smooth;
        if (config.line_symbol !== undefined) s.symbol = config.line_symbol;
        if (config.line_area === true) s.areaStyle = { ...(s.areaStyle || {}) };
      }

      if (s.type === "bar" && config.bar_stack === true) {
        s.stack = "total";
      }

      if (config.mark_point === true) {
        s.markPoint = {
          data: [
            { type: "max", name: "Max" },
            { type: "min", name: "Min" },
          ],
        };
      }

      if (config.mark_line === true) {
        s.markLine = {
          data: [{ type: "average", name: "Avg" }],
        };
      }

      return s;
    });
  }

  return opt as echarts.EChartsOption;
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
    case "line_bar":
    case "area_bar": {
      const metric2 = config.value_column || config.group_column || config.y_column;
      return {
        ...base,
        xAxis: { type: "category", data: xData },
        yAxis: { type: "value" },
        series: [
          { data: yData, type: "bar", name: config.y_column },
          {
            data: table.rows.map((row) => toNumber(row[metric2])),
            type: "line",
            name: metric2,
            smooth: true,
            ...(chartType === "area_bar" ? { areaStyle: { opacity: 0.3 } } : {}),
          },
        ],
        legend: { bottom: 0 },
      };
    }
    case "dual_axis": {
      const metric2 = config.value_column || config.group_column || config.y_column;
      return {
        ...base,
        xAxis: { type: "category", data: xData },
        yAxis: [
          { type: "value", name: config.y_column },
          { type: "value", name: metric2 },
        ],
        series: [
          { data: yData, type: "bar", name: config.y_column },
          {
            data: table.rows.map((row) => toNumber(row[metric2])),
            type: "line",
            name: metric2,
            yAxisIndex: 1,
            smooth: true,
          },
        ],
        legend: { bottom: 0 },
      };
    }
    case "stacked_area": {
      const { categories, series } = pivotSeries(
        table,
        config.x_column,
        config.y_column,
        config.group_column
      );
      return {
        ...base,
        xAxis: { type: "category", data: categories },
        yAxis: { type: "value" },
        series: series.map((s) => ({
          name: s.name,
          type: "line",
          stack: "total",
          areaStyle: {},
          data: s.data,
        })),
        legend: { bottom: 0 },
      };
    }
    case "grouped_line": {
      const { categories, series } = pivotSeries(
        table,
        config.x_column,
        config.y_column,
        config.group_column
      );
      return {
        ...base,
        xAxis: { type: "category", data: categories },
        yAxis: { type: "value" },
        series: series.map((s) => ({
          name: s.name,
          type: "line",
          smooth: true,
          data: s.data,
        })),
        legend: { bottom: 0 },
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

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const clean = hex.replace("#", "");
  if (clean.length !== 6) return null;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  if (isNaN(r) || isNaN(g) || isNaN(b)) return null;
  return { r, g, b };
}

function rgbToHex(r: number, g: number, b: number): string {
  return `#${[r, g, b].map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("")}`;
}

function shade(hex: string, factor: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  return rgbToHex(rgb.r * (1 - factor) + 0 * factor, rgb.g * (1 - factor) + 0 * factor, rgb.b * (1 - factor) + 0 * factor);
}

function alpha(hex: string, a: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${a})`;
}

function premiumGradient(color: string, vertical = true, dark = true): any {
  return new echarts.graphic.LinearGradient(
    0,
    0,
    vertical ? 0 : 1,
    vertical ? 1 : 0,
    [
      { offset: 0, color },
      { offset: 1, color: shade(color, dark ? 0.5 : 0.2) },
    ]
  );
}

function applyPremiumStyling(option: echarts.EChartsOption, theme: Theme): void {
  if (!option.series) return;
  const seriesArr = Array.isArray(option.series) ? option.series : [option.series];
  const isDark = theme.name === "premium";
  const barShadow = isDark ? "rgba(0,0,0,0.25)" : "rgba(0,0,0,0.1)";
  const lineShadow = isDark ? "rgba(0,0,0,0.3)" : "rgba(0,0,0,0.12)";
  const scatterShadow = isDark ? "rgba(0,0,0,0.4)" : "rgba(0,0,0,0.15)";
  const graphShadow = isDark ? "rgba(0,0,0,0.4)" : "rgba(0,0,0,0.15)";

  seriesArr.forEach((series: any, index) => {
    if (!series) return;
    const color = theme.palette[index % theme.palette.length];

    switch (series.type) {
      case "bar": {
        series.itemStyle = {
          borderRadius: [6, 6, 0, 0],
          shadowBlur: 6,
          shadowColor: barShadow,
          ...(isDark ? { color: premiumGradient(color, true, true) } : {}),
          ...series.itemStyle,
        };
        break;
      }
      case "line": {
        series.smooth = true;
        series.lineStyle = { width: 3, ...series.lineStyle };
        series.symbolSize = 6;
        series.itemStyle = {
          shadowBlur: 8,
          shadowColor: lineShadow,
          ...series.itemStyle,
        };
        if (series.areaStyle) {
          series.areaStyle = {
            opacity: 0.3,
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: alpha(color, isDark ? 0.45 : 0.35) },
              { offset: 1, color: alpha(color, 0.05) },
            ]),
            ...series.areaStyle,
          };
        }
        break;
      }
      case "scatter": {
        series.symbolSize = series.symbolSize ?? 10;
        series.itemStyle = {
          opacity: 0.85,
          shadowBlur: 8,
          shadowColor: scatterShadow,
          ...series.itemStyle,
        };
        break;
      }
      case "pie": {
        series.itemStyle = {
          borderRadius: 8,
          borderColor: theme.backgroundColor,
          borderWidth: 3,
          ...series.itemStyle,
        };
        series.label = { color: theme.textColor, ...series.label };
        break;
      }
      case "boxplot": {
        series.itemStyle = {
          color: alpha(color, 0.25),
          borderColor: color,
          borderWidth: 2,
          ...series.itemStyle,
        };
        break;
      }
      case "candlestick": {
        series.itemStyle = {
          color: "#34D399",
          color0: "#F87171",
          borderColor: "#34D399",
          borderColor0: "#F87171",
          ...series.itemStyle,
        };
        break;
      }
      case "funnel": {
        series.gap = 2;
        series.itemStyle = {
          borderColor: theme.backgroundColor,
          borderWidth: 2,
          ...series.itemStyle,
        };
        series.label = { color: theme.textColor, ...series.label };
        break;
      }
      case "sunburst": {
        series.itemStyle = {
          borderRadius: 6,
          borderColor: theme.backgroundColor,
          borderWidth: 2,
          ...series.itemStyle,
        };
        break;
      }
      case "radar": {
        series.lineStyle = { width: 3, ...series.lineStyle };
        series.areaStyle = { opacity: 0.2, ...series.areaStyle };
        series.symbolSize = 6;
        series.itemStyle = {
          shadowBlur: 8,
          shadowColor: lineShadow,
          ...series.itemStyle,
        };
        break;
      }
      case "graph": {
        series.lineStyle = { opacity: 0.6, curveness: 0.2, ...series.lineStyle };
        series.itemStyle = {
          shadowBlur: 8,
          shadowColor: graphShadow,
          ...series.itemStyle,
        };
        break;
      }
      default:
        break;
    }
  });
}

function renderDataTableHtml(table: DataTable, theme: Theme): string {
  const rows = table.rows.slice(0, 100);
  const header = table.columns
    .map((col) => `<th style="padding:8px 12px;border-bottom:2px solid ${theme.axisColor};text-align:left;background:${theme.name === "dark" || theme.name === "premium" ? "#2a2a2a" : "#f6f7f9"}">${escapeHtml(col)}</th>`)
    .join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${table.columns
          .map((col) => `<td style="padding:6px 12px;border-bottom:1px solid ${theme.splitLineColor || "#e5e7eb"}">${escapeHtml(String(row[col] ?? ""))}</td>`)
          .join("")}</tr>`
    )
    .join("");
  const caption =
    table.rows.length > 100
      ? `<p style="margin:8px 0 0;color:${theme.axisColor};font-size:12px">Showing first 100 of ${table.rows.length} rows.</p>`
      : "";
  return `
  <div class="container" style="margin-top:16px">
    <table style="width:100%;border-collapse:collapse;font-size:13px;color:${theme.textColor}">
      <thead><tr>${header}</tr></thead>
      <tbody>${body}</tbody>
    </table>
    ${caption}
  </div>`;
}

function wrapStaticSvgHtml(svg: string, title: string, theme: Theme): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <style>
    body { margin: 0; padding: 24px; background: ${theme.backgroundColor}; color: ${theme.textColor}; font-family: ${theme.fontFamily}; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    .container { background: ${theme.name === "dark" ? "#1f1f1f" : theme.name === "premium" ? "#0F172A" : theme.backgroundColor}; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  </style>
</head>
<body>
  <div class="container">
    ${svg}
  </div>
</body>
</html>`;
}

function violinSvg(
  table: DataTable,
  config: ChartConfig,
  theme: Theme,
  width: number,
  height: number
): string {
  const margin = { top: 60, right: 40, bottom: 70, left: 70 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const xCol = config.x_column;
  const yCol = config.y_column;

  const groups = new Map<string, number[]>();
  for (const row of table.rows) {
    const cat = String(row[xCol] ?? "");
    const val = toNumberStat(row[yCol]);
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat)!.push(val);
  }
  const categories = Array.from(groups.keys());
  const slot = innerW / categories.length;
  const maxHalfWidth = slot * 0.35;

  const allValues = Array.from(groups.values()).flat();
  const yNorm = normalizeStat(allValues);
  const yToPx = (v: number) => margin.top + innerH - yNorm.scale(v) * innerH;

  const shapes = categories
    .map((cat, i) => {
      const values = groups.get(cat)!;
      const xCenter = margin.left + i * slot + slot / 2;
      const color = theme.palette[i % theme.palette.length];
      const { xs, densities } = kde(values, 50);
      const maxDensity = Math.max(...densities, 1e-9);
      const left: [number, number][] = [];
      const right: [number, number][] = [];
      for (let k = 0; k < xs.length; k++) {
        const y = yToPx(xs[k]);
        const half = (densities[k] / maxDensity) * maxHalfWidth;
        left.push([xCenter - half, y]);
        right.push([xCenter + half, y]);
      }
      const path =
        "M " +
        left.map((p) => p.join(",")).join(" L ") +
        " L " +
        right.reverse().map((p) => p.join(",")).join(" L ") +
        " Z";
      return `<path d="${path}" fill="${color}" fill-opacity="0.6" stroke="${color}" stroke-width="1.5" />`;
    })
    .join("\n");

  return buildStatSvgWrapper(
    width,
    height,
    margin,
    innerW,
    innerH,
    config.title,
    xCol,
    yCol,
    categories,
    yNorm,
    theme,
    shapes
  );
}

function errorbarSvg(
  table: DataTable,
  config: ChartConfig,
  theme: Theme,
  width: number,
  height: number
): string {
  const margin = { top: 60, right: 40, bottom: 70, left: 70 };
  const innerW = width - margin.left - margin.right;
  const innerH = height - margin.top - margin.bottom;
  const xCol = config.x_column;
  const yCol = config.y_column;
  const lowerCol = config.lower_column!;
  const upperCol = config.upper_column!;

  const rows = table.rows;
  const xIsNumeric = rows.every((r) => Number.isFinite(toNumberStat(r[xCol])));
  let categories: string[] = [];
  const xPos = (row: Record<string, string | number>, i: number): number => {
    if (xIsNumeric) {
      const vals = rows.map((r) => toNumberStat(r[xCol]));
      const min = Math.min(...vals);
      const max = Math.max(...vals);
      const range = max - min || 1;
      return margin.left + ((toNumberStat(row[xCol]) - min) / range) * innerW;
    }
    if (categories.length === 0) categories = rows.map((r) => String(r[xCol]));
    const slot = innerW / rows.length;
    return margin.left + i * slot + slot / 2;
  };

  const yVals = rows.flatMap((r) => [
    toNumberStat(r[yCol]),
    toNumberStat(r[lowerCol]),
    toNumberStat(r[upperCol]),
  ]);
  const yNorm = normalizeStat(yVals);
  const yToPx = (v: number) => margin.top + innerH - yNorm.scale(v) * innerH;

  const cap = 10;
  const color = theme.palette[0];
  const shapes = rows
    .map((row, i) => {
      const x = xPos(row, i);
      const y = yToPx(toNumberStat(row[yCol]));
      const lo = yToPx(toNumberStat(row[lowerCol]));
      const hi = yToPx(toNumberStat(row[upperCol]));
      return `
        <line x1="${x}" y1="${lo}" x2="${x}" y2="${hi}" stroke="${color}" stroke-width="2" />
        <line x1="${x - cap / 2}" y1="${lo}" x2="${x + cap / 2}" y2="${lo}" stroke="${color}" stroke-width="2" />
        <line x1="${x - cap / 2}" y1="${hi}" x2="${x + cap / 2}" y2="${hi}" stroke="${color}" stroke-width="2" />
        <circle cx="${x}" cy="${y}" r="4" fill="${color}" />
      `;
    })
    .join("\n");

  if (!xIsNumeric && categories.length === 0) {
    categories = rows.map((r) => String(r[xCol]));
  }

  return buildStatSvgWrapper(
    width,
    height,
    margin,
    innerW,
    innerH,
    config.title,
    xCol,
    yCol,
    xIsNumeric ? [] : categories,
    yNorm,
    theme,
    shapes
  );
}

function buildStatSvgWrapper(
  width: number,
  height: number,
  margin: { top: number; right: number; bottom: number; left: number },
  innerW: number,
  innerH: number,
  title: string,
  xName: string,
  yName: string,
  categories: string[],
  yNorm: { min: number; max: number; scale: (v: number) => number },
  theme: Theme,
  shapes: string
): string {
  const xAxisY = margin.top + innerH;
  const xAxisLine = `<line x1="${margin.left}" y1="${xAxisY}" x2="${margin.left + innerW}" y2="${xAxisY}" stroke="${theme.axisColor}" stroke-width="1.5" />`;
  const yAxisLine = `<line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${xAxisY}" stroke="${theme.axisColor}" stroke-width="1.5" />`;

  const xLabels =
    categories.length > 0
      ? categories
          .map((cat, i) => {
            const slot = innerW / categories.length;
            const x = margin.left + i * slot + slot / 2;
            return `<text x="${x}" y="${xAxisY + 20}" font-family="${theme.fontFamily}" font-size="12" fill="${theme.textColor}" text-anchor="middle">${escapeHtml(cat)}</text>`;
          })
          .join("")
      : "";

  const yTicks = [0, 0.25, 0.5, 0.75, 1]
    .map((t) => {
      const val = yNorm.min + (yNorm.max - yNorm.min) * t;
      const y = margin.top + innerH - t * innerH;
      return `<text x="${margin.left - 10}" y="${y + 4}" font-family="${theme.fontFamily}" font-size="11" fill="${theme.textColor}" text-anchor="end">${val.toFixed(0)}</text>
    <line x1="${margin.left}" y1="${y}" x2="${margin.left + innerW}" y2="${y}" stroke="${theme.splitLineColor}" stroke-width="0.5" />`;
    })
    .join("");

  const titleText = `<text x="${width / 2}" y="32" font-family="${theme.fontFamily}" font-size="18" font-weight="bold" text-anchor="middle" fill="${theme.textColor}">${escapeHtml(title)}</text>`;
  const xLabelText = `<text x="${margin.left + innerW / 2}" y="${height - 18}" font-family="${theme.fontFamily}" font-size="13" fill="${theme.textColor}" text-anchor="middle">${escapeHtml(xName)}</text>`;
  const yLabelText = `<text transform="rotate(-90)" x="-${margin.top + innerH / 2}" y="18" font-family="${theme.fontFamily}" font-size="13" fill="${theme.textColor}" text-anchor="middle">${escapeHtml(yName)}</text>`;

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
    <rect width="100%" height="100%" fill="${theme.backgroundColor}" />
    ${titleText}
    ${xAxisLine}
    ${yAxisLine}
    ${yTicks}
    ${shapes}
    ${xLabels}
    ${xLabelText}
    ${yLabelText}
  </svg>`;
}

function toNumberStat(value: unknown): number {
  if (typeof value === "number") return value;
  if (typeof value === "string" && value !== "") {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

function normalizeStat(values: number[], pad = 0.05) {
  const finite = values.filter((v) => Number.isFinite(v));
  let min = finite.length ? Math.min(...finite) : 0;
  let max = finite.length ? Math.max(...finite) : 0;
  if (min === max) {
    min = min - 1;
    max = max + 1;
  }
  const range = max - min;
  return {
    min,
    max,
    scale: (v: number) => pad + ((v - min) / range) * (1 - pad * 2),
  };
}

function std(values: number[]): number {
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
  return Math.sqrt(variance);
}

function gaussianKernel(u: number): number {
  return Math.exp(-0.5 * u * u) / Math.sqrt(2 * Math.PI);
}

function kde(values: number[], nPoints: number): { xs: number[]; densities: number[] } {
  const sorted = [...values].sort((a, b) => a - b);
  let min = sorted[0];
  let max = sorted[sorted.length - 1];
  let range = max - min;
  if (range === 0) {
    range = Math.max(Math.abs(min), 1);
    min -= range * 0.2;
    max += range * 0.2;
    range = max - min;
  }
  const sd = std(values);
  let h = 1.06 * sd * Math.pow(values.length, -1 / 5);
  if (!Number.isFinite(h) || h === 0) h = range / 4;

  const xs: number[] = [];
  const densities: number[] = [];
  for (let i = 0; i < nPoints; i++) {
    const x = min + (i / (nPoints - 1)) * range;
    xs.push(x);
    let sum = 0;
    for (const v of values) sum += gaussianKernel((x - v) / h);
    densities.push(sum / (values.length * h));
  }
  return { xs, densities };
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
