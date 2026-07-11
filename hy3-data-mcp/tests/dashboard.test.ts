import { describe, it, expect } from "vitest";
import { renderDashboardHtml } from "../src/viz/echarts.js";

const table = {
  columns: ["month", "sales"],
  rows: [
    { month: "Jan", sales: 100 },
    { month: "Feb", sales: 150 },
    { month: "Mar", sales: 120 },
  ],
  raw: "month,sales\nJan,100\nFeb,150\nMar,120",
};

const chart = {
  chartType: "bar" as const,
  table,
  config: { title: "Monthly Sales", x_column: "month", y_column: "sales" },
};

describe("renderDashboardHtml", () => {
  it.each(["default", "hero", "compact", "rows", "columns"] as const)(
    "renders a dashboard with layout %s",
    (layout) => {
      const html = renderDashboardHtml([chart, chart], "Sales Dashboard", "nature", undefined, {}, layout);
      expect(html).toContain("<html");
      expect(html).toContain("Sales Dashboard");
      expect(html).toContain("echarts.init");
      expect(html).toContain("Monthly Sales");
    }
  );

  it("applies a custom font family", () => {
    const html = renderDashboardHtml([chart], "Font Test", "nature", "Inter");
    expect(html).toContain("Inter");
  });

  it("applies color overrides", () => {
    const html = renderDashboardHtml([chart], "Color Test", "nature", undefined, {
      backgroundColor: "#fafbfc",
      textColor: "#111111",
    });
    expect(html).toContain("#fafbfc");
    expect(html).toContain("#111111");
  });

  it("renders KPI cards by default", () => {
    const html = renderDashboardHtml([chart], "KPI Test", "nature");
    expect(html).toContain("kpi-row");
    expect(html).toContain("Total sales");
    expect(html).toContain("370");
  });

  it("can disable KPI cards", () => {
    const html = renderDashboardHtml([chart], "No KPI Test", "nature", undefined, {}, "grid", false);
    expect(html).not.toContain('<div class="kpi-row">');
  });

  it("adds a theme switcher when enabled", () => {
    const html = renderDashboardHtml(
      [chart],
      "Theme Switcher Test",
      "nature",
      undefined,
      {},
      "grid",
      true,
      "en",
      true
    );
    expect(html).toContain("dashboardThemeSwitcher");
    expect(html).toContain("registerTheme");
  });
});
