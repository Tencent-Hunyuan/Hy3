import { describe, it, expect } from "vitest";
import { getTheme, applyTheme, themes } from "../src/viz/themes.js";

describe("getTheme", () => {
  it("defaults to nature", () => {
    const theme = getTheme();
    expect(theme.name).toBe("nature");
  });

  it("falls back to nature for unknown theme names", () => {
    const theme = getTheme("unknown-theme" as any);
    expect(theme.name).toBe("nature");
  });

  it.each(Object.keys(themes))("returns theme %s", (name) => {
    const theme = getTheme(name);
    expect(theme.palette.length).toBeGreaterThan(0);
    expect(theme.backgroundColor).toBeDefined();
    expect(theme.textColor).toBeDefined();
  });

  it("applies color overrides", () => {
    const theme = getTheme("light", undefined, {
      backgroundColor: "#111",
      textColor: "#eee",
      axisColor: "#555",
      splitLineColor: "#333",
    });
    expect(theme.backgroundColor).toBe("#111");
    expect(theme.textColor).toBe("#eee");
    expect(theme.axisColor).toBe("#555");
    expect(theme.splitLineColor).toBe("#333");
  });

  it("applies a custom font family", () => {
    const theme = getTheme("nature", "Inter");
    expect(theme.fontFamily).toContain("Inter");
  });
});

describe("applyTheme", () => {
  it("merges theme into an ECharts option", () => {
    const theme = getTheme("nature");
    const option = applyTheme({ xAxis: { type: "category" }, yAxis: { type: "value" } }, theme);

    expect(option.backgroundColor).toBe(theme.backgroundColor);
    expect(option.color).toEqual(theme.palette);
    expect(option.textStyle).toMatchObject({ color: theme.textColor, fontFamily: theme.fontFamily });

    const xAxis = Array.isArray(option.xAxis) ? option.xAxis[0] : option.xAxis;
    expect(xAxis?.axisLine?.lineStyle?.color).toBe(theme.axisColor);

    const yAxis = Array.isArray(option.yAxis) ? option.yAxis[0] : option.yAxis;
    expect(yAxis?.axisLabel?.color).toBe(theme.textColor);
  });
});
