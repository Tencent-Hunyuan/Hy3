import { getTheme } from "./themes.js";
import type { Theme } from "./themes.js";
import type { DataTable } from "../utils.js";
import type { ChartConfig } from "./echarts.js";

export const CHART3D_TYPES = ["bar3d", "scatter3d", "line3d"] as const;
export type Chart3DType = (typeof CHART3D_TYPES)[number];

export function is3dChartType(type: string): type is Chart3DType {
  return (CHART3D_TYPES as readonly string[]).includes(type);
}

const COS30 = Math.cos(Math.PI / 6);
const SIN30 = Math.sin(Math.PI / 6);

interface NormalizedPoint {
  x: number;
  y: number;
  z: number;
  meta?: Record<string, string | number>;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
 .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function toNumber(value: unknown): number {
  if (typeof value === "number") return value;
  if (typeof value === "string" && value !== "") {
    const n = Number(value);
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

function normalize(
  values: number[],
  pad = 0.05
): { min: number; max: number; scale: (v: number) => number } {
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

function project(
  x: number,
  y: number,
  z: number,
  ox: number,
  oy: number,
  scale: number
): [number, number] {
  return [
    ox + (x - z) * COS30 * scale,
    oy - y * scale - (x + z) * SIN30 * 0.5 * scale,
  ];
}

function computeLayout(
  width: number,
  height: number,
  titleHeight: number,
  pad: number
): { ox: number; oy: number; scale: number } {
  const corners = [
    [0, 0, 0],
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
    [1, 1, 0],
    [1, 0, 1],
    [0, 1, 1],
    [1, 1, 1],
  ] as const;
  const raw = corners.map(([x, y, z]) => project(x, y, z, 0, 0, 1));
  const minX = Math.min(...raw.map((p) => p[0]));
  const maxX = Math.max(...raw.map((p) => p[0]));
  const minY = Math.min(...raw.map((p) => p[1]));
  const maxY = Math.max(...raw.map((p) => p[1]));

  const availW = width - pad * 2;
  const availH = height - pad - titleHeight;
  const scale = Math.min(availW / (maxX - minX), availH / (maxY - minY)) * 0.9;

  const ox = (pad + width - pad - (minX + maxX) * scale) / 2;
  const oy = (titleHeight + height - pad - (minY + maxY) * scale) / 2;
  return { ox, oy, scale };
}

function wrapSvg(
  width: number,
  height: number,
  title: string,
  theme: Theme,
  body: string
): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="${theme.backgroundColor}" />
  <text x="${width / 2}" y="32" font-family="${theme.fontFamily}" font-size="18" font-weight="bold" text-anchor="middle" fill="${theme.textColor}">${escapeHtml(title)}</text>
  ${body}
</svg>`;
}

function axisLabels(
  xLabel: string,
  yLabel: string,
  zLabel: string,
  ox: number,
  oy: number,
  scale: number,
  theme: Theme
): string {
  const pX = project(1.05, 0, 0, ox, oy, scale);
  const pY = project(0, 1.05, 0, ox, oy, scale);
  const pZ = project(0, 0, 1.05, ox, oy, scale);
  return `
    <text x="${pX[0]}" y="${pX[1]}" font-family="${theme.fontFamily}" font-size="12" fill="${theme.axisColor}" text-anchor="middle">${escapeHtml(xLabel)}</text>
    <text x="${pY[0]}" y="${pY[1]}" font-family="${theme.fontFamily}" font-size="12" fill="${theme.axisColor}" text-anchor="middle">${escapeHtml(yLabel)}</text>
    <text x="${pZ[0]}" y="${pZ[1]}" font-family="${theme.fontFamily}" font-size="12" fill="${theme.axisColor}" text-anchor="middle">${escapeHtml(zLabel)}</text>
  `;
}

function drawAxes(
  ox: number,
  oy: number,
  scale: number,
  theme: Theme
): string {
  const origin = project(0, 0, 0, ox, oy, scale);
  const xEnd = project(1, 0, 0, ox, oy, scale);
  const yEnd = project(0, 1, 0, ox, oy, scale);
  const zEnd = project(0, 0, 1, ox, oy, scale);
  return `
    <line x1="${origin[0]}" y1="${origin[1]}" x2="${xEnd[0]}" y2="${xEnd[1]}" stroke="${theme.axisColor}" stroke-width="1.5" />
    <line x1="${origin[0]}" y1="${origin[1]}" x2="${yEnd[0]}" y2="${yEnd[1]}" stroke="${theme.axisColor}" stroke-width="1.5" />
    <line x1="${origin[0]}" y1="${origin[1]}" x2="${zEnd[0]}" y2="${zEnd[1]}" stroke="${theme.axisColor}" stroke-width="1.5" />
  `;
}

function bar3dSvg(
  table: DataTable,
  config: ChartConfig,
  theme: Theme,
  width: number,
  height: number
): string {
  const xData = table.rows.map((row) => String(row[config.x_column] ?? ""));
  const yData = table.rows.map((row) => toNumber(row[config.y_column]));
  const yNorm = normalize(yData);
  const n = xData.length || 1;
  const slot = 1 / n;
  const barSize = slot * 0.55;

  const { ox, oy, scale } = computeLayout(width, height, 50, 32);

  const bars = table.rows
    .map((row, i) => ({
      label: String(row[config.x_column] ?? ""),
      value: yData[i],
      x: (i + 0.5) * slot,
      y: yNorm.scale(yData[i]),
      z: 0.5,
      color: theme.palette[i % theme.palette.length],
    }))
    .sort((a, b) => a.x - b.x);

  const faces: Array<{ path: string; color: string; depth: number }> = [];
  for (const bar of bars) {
    const x = bar.x - barSize / 2;
    const z = bar.z - barSize / 2;
    const w = barSize;
    const d = barSize;
    const h = bar.y;

    const depth = bar.x + bar.z + h;

    const basePts = {
      fl: project(x, 0, z, ox, oy, scale),
      fr: project(x + w, 0, z, ox, oy, scale),
      bl: project(x, 0, z + d, ox, oy, scale),
      br: project(x + w, 0, z + d, ox, oy, scale),
      tfl: project(x, h, z, ox, oy, scale),
      tfr: project(x + w, h, z, ox, oy, scale),
      tbl: project(x, h, z + d, ox, oy, scale),
      tbr: project(x + w, h, z + d, ox, oy, scale),
    };

    const topPath = `M ${basePts.tfl.join(",")} L ${basePts.tfr.join(",")} L ${basePts.tbr.join(",")} L ${basePts.tbl.join(",")} Z`;
    const leftPath = `M ${basePts.fl.join(",")} L ${basePts.tfl.join(",")} L ${basePts.tbl.join(",")} L ${basePts.bl.join(",")} Z`;
    const rightPath = `M ${basePts.fr.join(",")} L ${basePts.tfr.join(",")} L ${basePts.tbr.join(",")} L ${basePts.br.join(",")} Z`;

    faces.push({ path: topPath, color: bar.color, depth });
    faces.push({ path: leftPath, color: shade(bar.color, 0.2), depth });
    faces.push({ path: rightPath, color: shade(bar.color, 0.35), depth });

    // label on top
    const topCenter = project(x + w / 2, h, z + d / 2, ox, oy, scale);
    faces.push({
      path: `<text x="${topCenter[0]}" y="${topCenter[1] - 6}" font-family="${theme.fontFamily}" font-size="11" fill="${theme.textColor}" text-anchor="middle">${escapeHtml(bar.label)}</text>`,
      color: "",
      depth: depth + 1,
    });
  }

  faces.sort((a, b) => a.depth - b.depth);
  const shapes = faces
    .map((f) =>
      f.path.startsWith("<text")
        ? f.path
        : `<path d="${f.path}" fill="${f.color}" stroke="${theme.backgroundColor}" stroke-width="0.5" />`
    )
    .join("\n");

  // y-axis ticks
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const yTicks = ticks
    .map((t) => {
      const pt = project(0, t, 0, ox, oy, scale);
      const value = yNorm.min + (yNorm.max - yNorm.min) * t;
      return `<text x="${pt[0] - 8}" y="${pt[1]}" font-family="${theme.fontFamily}" font-size="11" fill="${theme.axisColor}" text-anchor="end">${value.toFixed(0)}</text>`;
    })
    .join("\n");

  const body = `
    ${drawAxes(ox, oy, scale, theme)}
    ${axisLabels(config.x_column, config.y_column, "", ox, oy, scale, theme)}
    ${shapes}
    ${yTicks}
  `;
  return wrapSvg(width, height, config.title, theme, body);
}

function scatter3dSvg(
  table: DataTable,
  config: ChartConfig,
  theme: Theme,
  width: number,
  height: number
): string {
  const xData = table.rows.map((row) => toNumber(row[config.x_column]));
  const yData = table.rows.map((row) => toNumber(row[config.y_column]));
  const zCol = config.z_column || config.value_column || config.y_column;
  const zData = table.rows.map((row) => toNumber(row[zCol]));

  const xNorm = normalize(xData);
  const yNorm = normalize(yData);
  const zNorm = normalize(zData);

  const points: Array<NormalizedPoint & { color: string }> = table.rows.map(
    (_row, i) => ({
      x: xNorm.scale(xData[i]),
      y: yNorm.scale(yData[i]),
      z: zNorm.scale(zData[i]),
      meta: { x: xData[i], y: yData[i], z: zData[i] },
      color: theme.palette[i % theme.palette.length],
    })
  );

  const { ox, oy, scale } = computeLayout(width, height, 50, 32);

  points.sort((a, b) => a.x + a.z + a.y - (b.x + b.z + b.y));

  const dots = points
    .map((p) => {
      const pt = project(p.x, p.y, p.z, ox, oy, scale);
      return `<circle cx="${pt[0]}" cy="${pt[1]}" r="5" fill="${p.color}" stroke="${theme.backgroundColor}" stroke-width="1" opacity="0.9" />`;
    })
    .join("\n");

  const body = `
    ${drawAxes(ox, oy, scale, theme)}
    ${axisLabels(config.x_column, config.y_column, zCol, ox, oy, scale, theme)}
    ${dots}
  `;
  return wrapSvg(width, height, config.title, theme, body);
}

function line3dSvg(
  table: DataTable,
  config: ChartConfig,
  theme: Theme,
  width: number,
  height: number
): string {
  const xData = table.rows.map((row) => toNumber(row[config.x_column]));
  const yData = table.rows.map((row) => toNumber(row[config.y_column]));
  const zCol = config.z_column || config.value_column || config.y_column;
  const zData = table.rows.map((row) => toNumber(row[zCol]));

  const xNorm = normalize(xData);
  const yNorm = normalize(yData);
  const zNorm = normalize(zData);

  const indexed = table.rows
    .map((_row, i) => ({
      x: xNorm.scale(xData[i]),
      y: yNorm.scale(yData[i]),
      z: zNorm.scale(zData[i]),
      order: xData[i],
    }))
    .sort((a, b) => a.order - b.order);

  const { ox, oy, scale } = computeLayout(width, height, 50, 32);

  const projected = indexed.map((p) => project(p.x, p.y, p.z, ox, oy, scale));
  const pathD = "M " + projected.map((p) => p.join(",")).join(" L ");
  const line = `<path d="${pathD}" fill="none" stroke="${theme.palette[0]}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />`;

  const dots = indexed
    .map((p, i) => ({ p: project(p.x, p.y, p.z, ox, oy, scale), i, depth: p.x + p.y + p.z }))
    .sort((a, b) => a.depth - b.depth)
    .map(
      ({ p, i }) =>
        `<circle cx="${p[0]}" cy="${p[1]}" r="4" fill="${theme.palette[i % theme.palette.length]}" stroke="${theme.backgroundColor}" stroke-width="1" />`
    )
    .join("\n");

  const body = `
    ${drawAxes(ox, oy, scale, theme)}
    ${axisLabels(config.x_column, config.y_column, zCol, ox, oy, scale, theme)}
    ${line}
    ${dots}
  `;
  return wrapSvg(width, height, config.title, theme, body);
}

function shade(hex: string, factor: number): string {
  const clean = hex.replace("#", "");
  if (clean.length !== 6) return hex;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return hex;
  const f = Math.max(0, Math.min(1, factor));
  const nr = Math.round(r * (1 - f));
  const ng = Math.round(g * (1 - f));
  const nb = Math.round(b * (1 - f));
  return `#${[nr, ng, nb]
    .map((v) => v.toString(16).padStart(2, "0"))
    .join("")}`;
}

export function render3dSvg(
  chartType: Chart3DType,
  table: DataTable,
  config: ChartConfig
): string {
  const width = config.width ?? 800;
  const height = config.height ?? 500;
  const theme = getTheme(config.theme, config.font_family);

  switch (chartType) {
    case "bar3d":
      return bar3dSvg(table, config, theme, width, height);
    case "scatter3d":
      return scatter3dSvg(table, config, theme, width, height);
    case "line3d":
      return line3dSvg(table, config, theme, width, height);
    default:
      return wrapSvg(
        width,
        height,
        config.title,
        theme,
        `<text x="${width / 2}" y="${height / 2}" font-family="${theme.fontFamily}" font-size="16" fill="${theme.textColor}" text-anchor="middle">Unsupported 3D chart type</text>`
      );
  }
}

export function render3dWebGlHtml(
  chartType: Chart3DType,
  table: DataTable,
  config: ChartConfig
): string {
  const width = config.width ?? 800;
  const height = config.height ?? 500;
  const theme = getTheme(config.theme, config.font_family);
  const title = config.title;
  const xCol = config.x_column;
  const yCol = config.y_column;
  const zCol = config.z_column || config.value_column || config.y_column;

  const axisStyle = {
    nameTextStyle: { color: theme.textColor, fontFamily: theme.fontFamily },
    axisLabel: { color: theme.textColor, fontFamily: theme.fontFamily },
    axisLine: { lineStyle: { color: theme.axisColor } },
    splitLine: { lineStyle: { color: theme.splitLineColor } },
  };

  const grid3D = {
    boxWidth: chartType === "bar3d" ? 200 : 160,
    boxDepth: chartType === "bar3d" ? 80 : 160,
    boxHeight: 100,
    viewControl: {
      projection: "perspective",
      autoRotate: false,
      alpha: 20,
      beta: 40,
      minDistance: 150,
      maxDistance: 600,
    },
    light: {
      main: { intensity: 1.2, shadow: true },
      ambient: { intensity: 0.3 },
    },
  };

  let option: any;

  if (chartType === "bar3d") {
    const categories = table.rows.map((row) => String(row[xCol] ?? ""));
    const data = table.rows.map((row, i) => [i, toNumber(row[yCol]), 0]);
    option = {
      backgroundColor: theme.backgroundColor,
      color: theme.palette,
      textStyle: { color: theme.textColor, fontFamily: theme.fontFamily },
      title: {
        text: title,
        textStyle: { color: theme.textColor, fontFamily: theme.fontFamily },
      },
      tooltip: {},
      xAxis3D: { type: "category", data: categories, name: xCol, ...axisStyle },
      yAxis3D: { type: "value", name: yCol, ...axisStyle },
      zAxis3D: { type: "category", data: [""], name: "", axisLabel: { show: false } },
      grid3D,
      series: [
        {
          type: "bar3D",
          data,
          shading: "lambert",
          label: { show: false },
          itemStyle: { opacity: 0.9 },
        },
      ],
    };
  } else {
    const data = table.rows.map((row) => [
      toNumber(row[xCol]),
      toNumber(row[yCol]),
      toNumber(row[zCol]),
    ]);
    const isScatter = chartType === "scatter3d";
    option = {
      backgroundColor: theme.backgroundColor,
      color: theme.palette,
      textStyle: { color: theme.textColor, fontFamily: theme.fontFamily },
      title: {
        text: title,
        textStyle: { color: theme.textColor, fontFamily: theme.fontFamily },
      },
      tooltip: {},
      xAxis3D: { type: "value", name: xCol, ...axisStyle },
      yAxis3D: { type: "value", name: yCol, ...axisStyle },
      zAxis3D: { type: "value", name: zCol, ...axisStyle },
      grid3D,
      series: [
        isScatter
          ? { type: "scatter3D", data, symbolSize: 12, itemStyle: { opacity: 0.85 } }
          : { type: "line3D", data, lineStyle: { width: 4 } },
      ],
    };
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(title)}</title>
  <style>
    body { margin: 0; padding: 24px; background: ${theme.backgroundColor}; color: ${theme.textColor}; font-family: ${theme.fontFamily}; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
    .container { background: ${theme.name === "dark" ? "#1f1f1f" : theme.name === "premium" ? "#0F172A" : theme.backgroundColor}; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    #chart { width: ${width}px; height: ${height}px; }
  </style>
</head>
<body>
  <div class="container">
    <div id="chart"></div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts-gl@2/dist/echarts-gl.min.js"></script>
  <script>
    const chart = echarts.init(document.getElementById('chart'));
    chart.setOption(${JSON.stringify(option)});
    window.addEventListener('resize', () => chart.resize());
  </script>
</body>
</html>`;
}
