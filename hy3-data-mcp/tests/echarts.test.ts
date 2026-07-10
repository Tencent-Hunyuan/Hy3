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
  ] as [ChartType, DataTable, Record<string, string>][])("renders a %s chart", (type, table, config) => {
    const svg = renderChartSvg(type, table, { title: `${type} chart`, ...config });
    expect(svg).toContain("<svg");
    expect(svg).toContain(`${type} chart`);
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
