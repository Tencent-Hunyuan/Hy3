import { describe, it, expect, vi } from "vitest";
import { mkdtemp, writeFile, readFile } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { handleToolCall } from "../src/tools/index.js";
import { Hy3Client } from "../src/client.js";

function createMockClient(response = "mocked response") {
  const chatImpl = async (_messages: unknown, options?: { onToken?: (token: string) => void }) => {
    if (options?.onToken) {
      options.onToken(response);
    }
    return response;
  };
  return {
    chat: vi.fn().mockImplementation(chatImpl),
    chatWithUsage: vi.fn().mockImplementation(async (_messages, options) => {
      const content = await chatImpl(_messages, options);
      return { content, usage: { prompt_tokens: 10, completion_tokens: 10, total_tokens: 20 } };
    }),
  } as unknown as Hy3Client;
}

describe("integration tests", () => {
  it("hy3_render_chart generates an SVG file", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "bar", x_column: "month", y_column: "sales", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("Data Chart");
  });

  it("hy3_render_chart applies custom colors", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      {
        file_path: dataFile,
        chart_type: "bar",
        x_column: "month",
        y_column: "sales",
        language: "en",
        background_color: "#f0f9ff",
        text_color: "#0f172a",
        palette: ["#ef4444", "#3b82f6"],
      },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("#f0f9ff");
    expect(svg).toContain("#0f172a");
    expect(svg).toContain("#ef4444");
  });

  it("hy3_render_wordcloud generates an SVG file", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_wordcloud",
      { text: "machine learning data science machine learning visualization data", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_render_chart renders a sankey SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "flow.csv");
    await writeFile(dataFile, "source,target,value\nA,X,10\nA,Y,20\nB,Y,15\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "sankey", x_column: "source", y_column: "target", value_column: "value", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_render_chart renders a boxplot SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "group,value\nA,10\nA,12\nA,15\nB,8\nB,14\nB,18\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "boxplot", x_column: "group", y_column: "value", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_render_chart renders a candlestick SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "stock.csv");
    await writeFile(
      dataFile,
      "date,open,close,low,high\n2024-01-01,100,105,98,110\n2024-01-02,105,103,101,108\n"
    );

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      {
        file_path: dataFile,
        chart_type: "candlestick",
        x_column: "date",
        y_column: "close",
        open_column: "open",
        close_column: "close",
        low_column: "low",
        high_column: "high",
        language: "en",
      },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("ecmeta_data_index");
  });

  it("hy3_render_chart renders a stacked bar SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,product,sales\nJan,A,10\nJan,B,20\nFeb,A,15\nFeb,B,25\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "stacked_bar", x_column: "month", y_column: "sales", group_column: "product", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_render_chart renders a bubble SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "x,y,size\n10,20,5\n15,25,10\n20,30,15\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "bubble", x_column: "x", y_column: "y", size_column: "size", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_render_chart renders a histogram SVG", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "value\n10\n12\n15\n18\n20\n22\n25\n28\n30\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "histogram", x_column: "value", y_column: "value", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
  });

  it("hy3_analyze_report generates an HTML report with embedded chart", async () => {
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
      "hy3_analyze_report",
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

  it("hy3_analyze_report generates a Markdown report", async () => {
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
      "hy3_analyze_report",
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

  it("hy3_analyze_report handles multiple files", async () => {
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
      "hy3_analyze_report",
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

  it("hy3_render_chart renders a 3D bar chart", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "bar3d", x_column: "month", y_column: "sales", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("Data Chart");
  });

  it("hy3_render_chart renders a 3D scatter chart", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "x,y,z\n10,20,5\n15,25,10\n20,30,15\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "scatter3d", x_column: "x", y_column: "y", z_column: "z", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("Data Chart");
  });

  it("hy3_render_chart renders a dual-axis chart", async () => {
    const dir = await mkdtemp(join(tmpdir(), "hy3-data-mcp-"));
    const dataFile = join(dir, "data.csv");
    await writeFile(dataFile, "month,sales,profit\nJan,100,20\nFeb,150,35\nMar,120,28\n");

    process.env.HY3_OUTPUT_DIR = join(dir, "output");

    const result = await handleToolCall(
      "hy3_render_chart",
      { file_path: dataFile, chart_type: "dual_axis", x_column: "month", y_column: "sales", value_column: "profit", language: "en" },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("<svg");
    expect(svg).toContain("Data Chart");
  });
});
