import type { EChartsOption } from "echarts";

export type ThemeName =
  "light" | "dark" | "colorful" | "minimal" | "professional" | "retro" | "science" | "nature";

export interface Theme {
  name: ThemeName;
  backgroundColor: string;
  textColor: string;
  axisColor: string;
  splitLineColor: string;
  fontFamily: string;
  palette: string[];
}

const baseFont =
  "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Microsoft YaHei', 'PingFang SC', sans-serif";

const serifFont = "Georgia, 'Times New Roman', 'Songti SC', 'SimSun', serif";

const monoFont = "'SF Mono', Monaco, Consolas, 'Courier New', monospace";

const natureFont =
  "'Inter', 'Helvetica Neue', Helvetica, Arial, 'Microsoft YaHei', 'PingFang SC', sans-serif";

export const themes: Record<ThemeName, Theme> = {
  light: {
    name: "light",
    backgroundColor: "#ffffff",
    textColor: "#24292f",
    axisColor: "#8c9197",
    splitLineColor: "#e5e7eb",
    fontFamily: baseFont,
    palette: [
      "#5470c6",
      "#91cc75",
      "#fac858",
      "#ee6666",
      "#73c0de",
      "#3ba272",
      "#fc8452",
      "#9a60b4",
      "#ea7ccc",
    ],
  },
  dark: {
    name: "dark",
    backgroundColor: "#1a1a1a",
    textColor: "#eeeeee",
    axisColor: "#555555",
    splitLineColor: "#333333",
    fontFamily: baseFont,
    palette: [
      "#4992ff",
      "#7cffb2",
      "#fddd60",
      "#ff6e76",
      "#58d9f9",
      "#05c091",
      "#ff8a45",
      "#8d48e3",
      "#dd79ff",
    ],
  },
  colorful: {
    name: "colorful",
    backgroundColor: "#f6f8fa",
    textColor: "#1f2937",
    axisColor: "#9ca3af",
    splitLineColor: "#e5e7eb",
    fontFamily: baseFont,
    palette: [
      "#ff6b6b",
      "#4ecdc4",
      "#45b7d1",
      "#f9ca24",
      "#6c5ce7",
      "#a29bfe",
      "#fd79a8",
      "#fdcb6e",
      "#55efc4",
    ],
  },
  minimal: {
    name: "minimal",
    backgroundColor: "#fafafa",
    textColor: "#374151",
    axisColor: "#d1d5db",
    splitLineColor: "#f3f4f6",
    fontFamily: baseFont,
    palette: [
      "#2563eb",
      "#7c3aed",
      "#db2777",
      "#ea580c",
      "#16a34a",
      "#0891b2",
      "#4f46e5",
      "#be123c",
      "#854d0e",
    ],
  },
  professional: {
    name: "professional",
    backgroundColor: "#ffffff",
    textColor: "#1e293b",
    axisColor: "#94a3b8",
    splitLineColor: "#e2e8f0",
    fontFamily: baseFont,
    palette: [
      "#0f172a",
      "#334155",
      "#475569",
      "#64748b",
      "#94a3b8",
      "#cbd5e1",
      "#0369a1",
      "#075985",
      "#0c4a6e",
    ],
  },
  retro: {
    name: "retro",
    backgroundColor: "#fdf6e3",
    textColor: "#433422",
    axisColor: "#b58900",
    splitLineColor: "#eee8d5",
    fontFamily: serifFont,
    palette: [
      "#b58900",
      "#cb4b16",
      "#dc322f",
      "#d33682",
      "#6c71c4",
      "#268bd2",
      "#2aa198",
      "#859900",
      "#073642",
    ],
  },
  science: {
    name: "science",
    backgroundColor: "#ffffff",
    textColor: "#111827",
    axisColor: "#6b7280",
    splitLineColor: "#e5e7eb",
    fontFamily: monoFont,
    palette: [
      "#00441b",
      "#006d2c",
      "#238b45",
      "#41ab5d",
      "#74c476",
      "#a1d99b",
      "#c7e9c0",
      "#e5f5e0",
      "#f7fcf5",
    ],
  },
  nature: {
    name: "nature",
    backgroundColor: "#ffffff",
    textColor: "#1a1a1a",
    axisColor: "#999999",
    splitLineColor: "#e8e8e8",
    fontFamily: natureFont,
    palette: [
      "#4E79A7",
      "#F28E2B",
      "#E15759",
      "#76B7B2",
      "#59A14F",
      "#EDC948",
      "#B07AA1",
      "#FF9DA7",
      "#9C755F",
    ],
  },
};

export function getTheme(
  theme?: string,
  fontFamily?: string,
  overrides?: Partial<Omit<Theme, "name">>
): Theme {
  const t = themes[(theme as ThemeName) || "nature"] ?? themes.nature;
  const merged: Theme = { ...t };
  if (overrides) {
    if (overrides.backgroundColor !== undefined) merged.backgroundColor = overrides.backgroundColor;
    if (overrides.textColor !== undefined) merged.textColor = overrides.textColor;
    if (overrides.axisColor !== undefined) merged.axisColor = overrides.axisColor;
    if (overrides.splitLineColor !== undefined) merged.splitLineColor = overrides.splitLineColor;
    if (overrides.fontFamily !== undefined) merged.fontFamily = overrides.fontFamily;
    if (overrides.palette !== undefined && overrides.palette.length > 0) {
      merged.palette = overrides.palette;
    }
  }
  if (fontFamily) {
    merged.fontFamily = fontFamily;
  }
  return merged;
}

export function applyTheme(option: EChartsOption, theme: Theme): EChartsOption {
  const merged: EChartsOption = {
    ...option,
    backgroundColor: theme.backgroundColor,
    color: theme.palette,
    textStyle: {
      color: theme.textColor,
      fontFamily: theme.fontFamily,
      ...(option.textStyle || {}),
    },
    title: {
      ...(option.title || {}),
      textStyle: {
        color: theme.textColor,
        fontFamily: theme.fontFamily,
        ...(option.title && (option.title as any).textStyle),
      },
    },
    legend: {
      ...(option.legend || {}),
      textStyle: {
        color: theme.textColor,
        fontFamily: theme.fontFamily,
        ...(option.legend && (option.legend as any).textStyle),
      },
    },
    tooltip: {
      ...(option.tooltip || {}),
      backgroundColor: theme.name === "dark" ? "rgba(30,30,30,0.9)" : "rgba(255,255,255,0.95)",
      borderColor: theme.splitLineColor,
      textStyle: {
        color: theme.textColor,
        fontFamily: theme.fontFamily,
      },
    },
  };

  const axisOption = {
    axisLine: { lineStyle: { color: theme.axisColor } },
    axisTick: { lineStyle: { color: theme.axisColor } },
    axisLabel: { color: theme.textColor, fontFamily: theme.fontFamily },
    splitLine: { lineStyle: { color: theme.splitLineColor } },
    nameTextStyle: { color: theme.textColor, fontFamily: theme.fontFamily },
  };

  if (merged.xAxis) {
    const axes = Array.isArray(merged.xAxis) ? merged.xAxis : [merged.xAxis];
    merged.xAxis = axes.map((a) => ({ ...axisOption, ...a }));
  }
  if (merged.yAxis) {
    const axes = Array.isArray(merged.yAxis) ? merged.yAxis : [merged.yAxis];
    merged.yAxis = axes.map((a) => ({ ...axisOption, ...a }));
  }

  if (merged.radar && (merged.radar as any).axisName) {
    (merged.radar as any).axisName = {
      color: theme.textColor,
      fontFamily: theme.fontFamily,
      ...(merged.radar as any).axisName,
    };
  }

  return merged;
}
