import { describe, it, expect, vi } from "vitest";
import { mkdtemp, writeFile, readFile } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { handleToolCall } from "../src/tools/index.js";
import { Hy3Client } from "../src/client.js";

function createMockClient(response = "mocked response") {
  return {
    chat: vi.fn().mockResolvedValue(response),
  } as unknown as Hy3Client;
}

describe("integration tests", () => {
  it("hy3_data_visualize generates an SVG file", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({ x_column: "month", y_column: "sales", title: "Sales Trend" })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "bar", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("Sales Trend");
  });

  it("hy3_data_visualize applies custom colors", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({ x_column: "month", y_column: "sales", title: "Custom Colors" })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      {
        file_path: dataFile,
        chart_type: "bar",
        language: "en",
        background_color: "#f0f9ff",
        text_color: "#0f172a",
        palette: ["#ef4444", "#3b82f6"],
      },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("#f0f9ff");
    expect(svg).toContain("#0f172a");
    expect(svg).toContain("#ef4444");
  });

  it("hy3_wordcloud generates an SVG file", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const textFile = join(dir, "text.txt");
    await writeFile(textFile, "machine learning data science machine learning visualization data");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify([
        { word: "machine", weight: 100 },
        { word: "learning", weight: 80 },
        { word: "data", weight: 60 },
      ])
    );
    const result = await handleToolCall(
      "hy3_wordcloud",
      { file_path: textFile, language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_data_visualize renders a sankey SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "flow.csv");
    await writeFile(dataFile, "source,target,value\nA,X,10\nA,Y,20\nB,Y,15\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({
        x_column: "source",
        y_column: "target",
        value_column: "value",
        title: "Flow",
      })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "sankey", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_data_visualize renders a boxplot SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "group,value\nA,10\nA,12\nA,15\nB,8\nB,14\nB,18\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({ x_column: "group", y_column: "value", title: "Distribution" })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "boxplot", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_data_visualize renders a candlestick SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "stock.csv");
    await writeFile(
      dataFile,
      "date,open,close,low,high\n2024-01-01,100,105,98,110\n2024-01-02,105,103,101,108\n"
    );

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({
        x_column: "date",
        open_column: "open",
        close_column: "close",
        low_column: "low",
        high_column: "high",
        title: "Stock",
      })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "candlestick", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_data_visualize renders a stacked bar SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,product,sales\nJan,A,10\nJan,B,20\nFeb,A,15\nFeb,B,25\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({
        x_column: "month",
        y_column: "sales",
        group_column: "product",
        title: "Sales",
      })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "stacked_bar", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_data_visualize renders a bubble SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "x,y,size\n10,20,5\n15,25,10\n20,30,15\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({ x_column: "x", y_column: "y", size_column: "size", title: "Bubble" })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "bubble", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_data_visualize renders a histogram SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "value\n10\n12\n15\n18\n20\n22\n25\n28\n30\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({ x_column: "value", y_column: "value", title: "Histogram" })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "histogram", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_data_report generates an HTML report with embedded chart", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({
        title: "Monthly Sales Report",
        overview: "Overview text",
        sections: [
          {
            heading: "Sales Trend",
            text: "Sales increased in February.",
            chart: {
              chart_type: "bar",
              x_column: "month",
              y_column: "sales",
              title: "Monthly Sales",
            },
          },
        ],
        conclusions: "Conclusion text",
      })
    );

    const result = await handleToolCall(
      "hy3_data_report",
      { file_paths: [dataFile], output_format: "html", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const htmlPath = match![1].trim();
    const html = await readFile(htmlPath, "utf-8");
    expect(html).toContain("<!DOCTYPE html>");
    expect(html).toContain("Monthly Sales Report");
    expect(html).toContain("data:image/png;base64,");
  });

  it("hy3_data_report generates a Markdown report", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({
        title: "Monthly Sales Report",
        overview: "Overview text",
        sections: [
          {
            heading: "Sales Trend",
            text: "Sales increased in February.",
            chart: {
              chart_type: "bar",
              x_column: "month",
              y_column: "sales",
              title: "Monthly Sales",
            },
          },
        ],
        conclusions: "Conclusion text",
      })
    );

    const result = await handleToolCall(
      "hy3_data_report",
      { file_paths: [dataFile], output_format: "markdown", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const mdPath = match![1].trim();
    expect(mdPath.endsWith(".md")).toBe(true);
    const md = await readFile(mdPath, "utf-8");
    expect(md).toContain("# Monthly Sales Report");
    expect(md).toContain("data:image/png;base64,");
  });

  it("hy3_data_report handles multiple files", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const salesFile = join(dir, "sales.csv");
    const usersFile = join(dir, "users.csv");
    await writeFile(salesFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");
    await writeFile(usersFile, "country,users\nUS,500\nUK,300\nDE,200\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({
        title: "Multi-File Report",
        overview: "Overview text",
        sections: [
          {
            heading: "Sales",
            text: "Sales trend.",
            chart: {
              file_path: salesFile,
              chart_type: "bar",
              x_column: "month",
              y_column: "sales",
              title: "Sales",
            },
          },
          {
            heading: "Users",
            text: "Users by country.",
            chart: {
              file_path: usersFile,
              chart_type: "bar",
              x_column: "country",
              y_column: "users",
              title: "Users",
            },
          },
        ],
        conclusions: "Conclusion text",
      })
    );

    const result = await handleToolCall(
      "hy3_data_report",
      { file_paths: [salesFile, usersFile], output_format: "html", language: "en" },
      client
    );

    expect(result.content[0].text).toContain("2 chart(s)");
    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const htmlPath = match![1].trim();
    const html = await readFile(htmlPath, "utf-8");
    expect(html).toContain("Multi-File Report");
    expect((html.match(/data:image\/png;base64,/g) || []).length).toBe(2);
  });

  it("hy3_data_visualize renders a 3D bar chart", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({ x_column: "month", y_column: "sales", title: "3D Sales" })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "bar3d", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("3D Sales");
  });

  it("hy3_data_visualize renders a 3D scatter chart", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "x,y,z\n10,20,5\n15,25,10\n20,30,15\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({ x_column: "x", y_column: "y", z_column: "z", title: "3D Scatter" })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "scatter3d", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("3D Scatter");
  });

  it("hy3_data_visualize renders a dual-axis chart", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales,profit\nJan,100,20\nFeb,150,35\nMar,120,28\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const client = createMockClient(
      JSON.stringify({
        x_column: "month",
        y_column: "sales",
        value_column: "profit",
        title: "Sales vs Profit",
      })
    );
    const result = await handleToolCall(
      "hy3_data_visualize",
      { file_path: dataFile, chart_type: "dual_axis", language: "en" },
      client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("Sales vs Profit");
  });
});
