import { describe, it, expect } from "vitest";
import {
  renderChartSvg,
  renderChartHtml,
  renderKnowledgeGraphSvg,
  renderKnowledgeGraphHtml,
} from "../src/viz/echarts.js";
import type { ChartType, DataTable } from "../src/viz/echarts.js";

const simpleTable: DataTable = {
  columns: ["month", "sales"],
  rows: [
    { month: "Jan", sales: 100 },
    { month: "Feb", sales: 150 },
    { month: "Mar", sales: 120 },
  ],
  raw: "month,sales\nJan,100\nFeb,150\nMar,120",
};

const groupedTable: DataTable = {
  columns: ["month", "product", "sales"],
  rows: [
    { month: "Jan", product: "A", sales: 10 },
    { month: "Jan", product: "B", sales: 20 },
    { month: "Feb", product: "A", sales: 15 },
    { month: "Feb", product: "B", sales: 25 },
  ],
  raw: "month,product,sales\nJan,A,10\nJan,B,20\nFeb,A,15\nFeb,B,25",
};

const bubbleTable: DataTable = {
  columns: ["x", "y", "size"],
  rows: [
    { x: 10, y: 20, size: 5 },
    { x: 15, y: 25, size: 10 },
  ],
  raw: "x,y,size\n10,20,5\n15,25,10",
};

const candlestickTable: DataTable = {
  columns: ["date", "open", "close", "low", "high"],
  rows: [
    { date: "2024-01-01", open: 100, close: 105, low: 98, high: 110 },
    { date: "2024-01-02", open: 105, close: 103, low: 101, high: 108 },
  ],
  raw: "date,open,close,low,high\n2024-01-01,100,105,98,110\n2024-01-02,105,103,101,108",
};

const sankeyTable: DataTable = {
  columns: ["source", "target", "value"],
  rows: [
    { source: "A", target: "X", value: 10 },
    { source: "A", target: "Y", value: 20 },
  ],
  raw: "source,target,value\nA,X,10\nA,Y,20",
};

const hierarchicalTable: DataTable = {
  columns: ["name", "value"],
  rows: [
    { name: "A", value: 10 },
    { name: "B", value: 20 },
  ],
  raw: "name,value\nA,10\nB,20",
};

const violinTable: DataTable = {
  columns: ["group", "value"],
  rows: [
    { group: "A", value: 10 },
    { group: "A", value: 12 },
    { group: "A", value: 14 },
    { group: "B", value: 20 },
    { group: "B", value: 22 },
    { group: "B", value: 18 },
  ],
  raw: "group,value\nA,10\nA,12\nA,14\nB,20\nB,22\nB,18",
};

const errorbarTable: DataTable = {
  columns: ["x", "y", "lower", "upper"],
  rows: [
    { x: "Q1", y: 100, lower: 80, upper: 120 },
    { x: "Q2", y: 130, lower: 110, upper: 150 },
    { x: "Q3", y: 90, lower: 70, upper: 110 },
  ],
  raw: "x,y,lower,upper\nQ1,100,80,120\nQ2,130,110,150\nQ3,90,70,110",
};

describe("renderChartSvg", () => {
  it.each([
    ["bar", simpleTable, { x_column: "month", y_column: "sales" }],
    ["line", simpleTable, { x_column: "month", y_column: "sales" }],
    ["area", simpleTable, { x_column: "month", y_column: "sales" }],
    ["pie", simpleTable, { x_column: "month", y_column: "sales" }],
    ["donut", simpleTable, { x_column: "month", y_column: "sales" }],
    ["rose", simpleTable, { x_column: "month", y_column: "sales" }],
    ["scatter", simpleTable, { x_column: "month", y_column: "sales" }],
    ["scatter_trend", simpleTable, { x_column: "month", y_column: "sales" }],
    ["radar", simpleTable, { x_column: "month", y_column: "sales" }],
    ["heatmap", simpleTable, { x_column: "month", y_column: "sales" }],
    ["funnel", simpleTable, { x_column: "month", y_column: "sales" }],
    ["sankey", sankeyTable, { x_column: "source", y_column: "target", value_column: "value" }],
    ["treemap", hierarchicalTable, { x_column: "name", y_column: "value" }],
    ["sunburst", hierarchicalTable, { x_column: "name", y_column: "value" }],
    ["gauge", simpleTable, { x_column: "month", y_column: "sales" }],
    ["histogram", simpleTable, { x_column: "sales", y_column: "sales" }],
    ["boxplot", groupedTable, { x_column: "product", y_column: "sales" }],
    ["candlestick", candlestickTable, { x_column: "date", open_column: "open", close_column: "close", low_column: "low", high_column: "high" }],
    ["stacked_bar", groupedTable, { x_column: "month", y_column: "sales", group_column: "product" }],
    ["grouped_bar", groupedTable, { x_column: "month", y_column: "sales", group_column: "product" }],
    ["bubble", bubbleTable, { x_column: "x", y_column: "y", size_column: "size" }],
    ["violin", violinTable, { x_column: "group", y_column: "value" }],
    ["errorbar", errorbarTable, { x_column: "x", y_column: "y", lower_column: "lower", upper_column: "upper" }],
  ] as [ChartType, DataTable, Record<string, string>][])("renders a %s chart", (type, table, config) => {
    const svg = renderChartSvg(type, table, { title: `${type} chart`, ...config });
    expect(svg).toContain("<svg");
    expect(svg).toContain(`${type} chart`);
  });

  it("renders candlestick bodies and wicks", () => {
    const svg = renderChartSvg("candlestick", candlestickTable, {
      title: "K-line",
      x_column: "date",
      open_column: "open",
      close_column: "close",
      low_column: "low",
      high_column: "high",
    });
    expect(svg).toContain("ecmeta_data_index");
  });
});

describe("renderChartHtml", () => {
  it("renders an interactive HTML page", () => {
    const html = renderChartHtml("bar", simpleTable, {
      title: "Bar Chart",
      x_column: "month",
      y_column: "sales",
      theme: "nature",
    });
    expect(html).toContain("<html");
    expect(html).toContain("Bar Chart");
    expect(html).toContain("echarts.init");
  });

  it("appends a data table when show_data_table is true", () => {
    const html = renderChartHtml("bar", simpleTable, {
      title: "Bar Chart",
      x_column: "month",
      y_column: "sales",
      theme: "nature",
      show_data_table: true,
    });
    expect(html).toContain("<table");
    expect(html).toContain("Jan");
    expect(html).toContain("Feb");
  });

  it("adds a theme switcher when enable_theme_switcher is true", () => {
    const html = renderChartHtml("bar", simpleTable, {
      title: "Bar Chart",
      x_column: "month",
      y_column: "sales",
      theme: "nature",
      enable_theme_switcher: true,
    });
    expect(html).toContain("themeSwitcher");
    expect(html).toContain("registerTheme");
  });
});

describe("renderChartHtml 3D WebGL", () => {
  const scatter3dTable: DataTable = {
    columns: ["x", "y", "z"],
    rows: [
      { x: 1, y: 2, z: 3 },
      { x: 4, y: 5, z: 6 },
    ],
    raw: "x,y,z\n1,2,3\n4,5,6",
  };

  it.each([
    ["bar3d", simpleTable, { x_column: "month", y_column: "sales" }],
    ["scatter3d", scatter3dTable, { x_column: "x", y_column: "y", z_column: "z" }],
    ["line3d", scatter3dTable, { x_column: "x", y_column: "y", z_column: "z" }],
  ] as [ChartType, DataTable, Record<string, string>][])(
    "renders interactive WebGL HTML for %s",
    (type, table, cfg) => {
      const html = renderChartHtml(type, table, {
        title: `${type} WebGL`,
        ...cfg,
        interactive_3d: true,
      } as any);
      expect(html).toContain("echarts-gl");
      expect(html).toContain("grid3D");
      expect(html).toContain(type.replace("3d", "3D"));
    }
  );
});

describe("renderKnowledgeGraph", () => {
  const nodes = [{ id: "A", group: 1 }, { id: "B", group: 2 }];
  const links = [{ source: "A", target: "B", relation: "links" }];

  it("renders a knowledge graph SVG", () => {
    const svg = renderKnowledgeGraphSvg(nodes, links, "Graph", 400, 300, "nature");
    expect(svg).toContain("<svg");
    expect(svg).toContain("Graph");
  });

  it("renders a knowledge graph HTML page", () => {
    const html = renderKnowledgeGraphHtml(nodes, links, "Graph", 400, 300, "nature");
    expect(html).toContain("<html");
    expect(html).toContain("Graph");
    expect(html).toContain("echarts.init");
  });
});
