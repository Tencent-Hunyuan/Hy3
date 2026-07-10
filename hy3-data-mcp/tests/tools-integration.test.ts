import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mkdtemp, writeFile, rm, readFile } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { handleToolCall } from "../src/tools/index.js";
import { Hy3Client } from "../src/client.js";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const sampleDir = join(__dirname, "..", "sample_data");

function createMockClient(response: string | string[] = "mocked response") {
  const queue = Array.isArray(response) ? [...response] : [response];
  const fn = vi.fn().mockImplementation(async (_messages, options) => {
    const next = queue.shift() ?? (Array.isArray(response) ? "" : response);
    if (options?.onToken) {
      options.onToken(next);
    }
    return next;
  });
  return { chat: fn } as unknown as Hy3Client;
}

describe("tool integration tests", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "hy3-tools-"));
    process.env.HY3_OUTPUT_DIR = join(tempDir, "output");
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
    delete process.env.HY3_OUTPUT_DIR;
  });

  it("hy3_plan_dashboard returns a JSON design", async () => {
    const dataFile = join(tempDir, "sales.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    const client = createMockClient(
      JSON.stringify({
        title: "Sales Dashboard",
        charts: [{ file_index: 0, chart_type: "bar", x_column: "month", y_column: "sales", title: "Sales" }],
      })
    );
    const progress = vi.fn();
    const result = await handleToolCall(
      "hy3_plan_dashboard",
      { file_paths: [dataFile], title: "Sales Dashboard", language: "en", layout: "grid" },
      client,
      progress
    );

    const design = JSON.parse(result.content[0].text);
    expect(design.title).toBe("Sales Dashboard");
    expect(design.charts[0].chart_type).toBe("bar");
    expect(progress).toHaveBeenCalled();
  });

  it("hy3_render_dashboard renders an HTML dashboard from a design", async () => {
    const dataFile = join(tempDir, "sales.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    const design = {
      title: "Sales Dashboard",
      layout: "grid",
      charts: [{ file_index: 0, chart_type: "bar", x_column: "month", y_column: "sales", title: "Sales" }],
    };
    const result = await handleToolCall(
      "hy3_render_dashboard",
      { file_paths: [dataFile], design, output_format: "html", language: "en" },
      {} as Hy3Client
    );

    expect(result.content[0].text).toContain("Sales Dashboard");
    expect(result.content[0].text).toContain("HTML");
  });

  it("hy3_render_dashboard renders a PNG dashboard from a design", async () => {
    const dataFile = join(tempDir, "sales.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    const design = {
      title: "PNG Dashboard",
      layout: "rows",
      charts: [{ file_index: 0, chart_type: "line", x_column: "month", y_column: "sales", title: "Sales" }],
    };
    const result = await handleToolCall(
      "hy3_render_dashboard",
      { file_paths: [dataFile], design, output_format: "png", language: "en" },
      {} as Hy3Client
    );

    expect(result.content[0].text).toContain("PNG");
  });

  it("hy3_plan_dashboard accepts inline data", async () => {
    const client = createMockClient(
      JSON.stringify({
        title: "Inline Dashboard",
        charts: [{ file_index: 0, chart_type: "bar", x_column: "month", y_column: "sales", title: "Sales" }],
      })
    );
    const result = await handleToolCall(
      "hy3_plan_dashboard",
      { data: '[{"month":"Jan","sales":100},{"month":"Feb","sales":150}]', language: "en" },
      client
    );

    const design = JSON.parse(result.content[0].text);
    expect(design.title).toBe("Inline Dashboard");
  });

  it("hy3_render_chart accepts inline data", async () => {
    const result = await handleToolCall(
      "hy3_render_chart",
      {
        data: '[{"month":"Jan","sales":100},{"month":"Feb","sales":150}]',
        chart_type: "bar",
        x_column: "month",
        y_column: "sales",
        output_format: "svg",
        language: "en",
      },
      {} as Hy3Client
    );

    expect(result.content[0].text).toContain("Data Chart");
    expect(result.content[0].text).toContain("SVG");
  });

  it("hy3_render_dashboard accepts inline data", async () => {
    const design = {
      title: "Inline Render",
      layout: "grid",
      charts: [{ file_index: 0, chart_type: "bar", x_column: "month", y_column: "sales", title: "Sales" }],
    };
    const result = await handleToolCall(
      "hy3_render_dashboard",
      {
        data: '[{"month":"Jan","sales":100},{"month":"Feb","sales":150}]',
        design,
        output_format: "html",
        language: "en",
      },
      {} as Hy3Client
    );

    expect(result.content[0].text).toContain("Inline Render");
    expect(result.content[0].text).toContain("HTML");
  });

  it("hy3_extract_document returns text and metadata for a DOCX", async () => {
    const docx = join(sampleDir, "report.docx");
    const result = await handleToolCall("hy3_extract_document", { file_path: docx }, {} as Hy3Client);
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.document_type).toBe("docx");
    expect(parsed.has_structured_data).toBe(false);
    expect(parsed.text.length).toBeGreaterThan(0);
    expect(parsed.structured_hint).toContain("hy3_analyze");
  });

  it("hy3_extract_document returns text and metadata for a PDF", async () => {
    const pdf = join(sampleDir, "report.pdf");
    const result = await handleToolCall("hy3_extract_document", { file_path: pdf }, {} as Hy3Client);
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.document_type).toBe("pdf");
    expect(parsed.has_structured_data).toBe(false);
    expect(parsed.text.length).toBeGreaterThan(0);
  });

  it("hy3_extract_document marks CSV as structured data", async () => {
    const csv = join(tempDir, "data.csv");
    await writeFile(csv, "a,b\n1,2\n3,4\n");
    const result = await handleToolCall("hy3_extract_document", { file_path: csv }, {} as Hy3Client);
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.document_type).toBe("csv");
    expect(parsed.has_structured_data).toBe(true);
    expect(parsed.structured_hint).toContain("hy3_render_chart");
  });

  it("hy3_analyze returns text analysis", async () => {
    const client = createMockClient("Summary text");
    const result = await handleToolCall(
      "hy3_analyze",
      { text: "This is a long report about sales trends.", question: "Summarize", output_format: "text", language: "en" },
      client
    );
    expect(result.content[0].text).toBe("Summary text");
  });

  it("hy3_analyze generates HTML report", async () => {
    const client = createMockClient("PDF summary");
    const result = await handleToolCall(
      "hy3_analyze",
      { text: "Annual report content.", question: "Summarize", output_format: "html", language: "en" },
      client
    );
    expect(result.content[0].text).toContain("HTML");
    expect(result.content[0].text).toContain("File path:");
  });

  it("hy3_analyze extracts structured JSON", async () => {
    const client = createMockClient(JSON.stringify({ key_metrics: ["revenue", "profit"], trends: ["up"] }));
    const result = await handleToolCall(
      "hy3_analyze",
      {
        text: "Q1 revenue grew 20% and profit margin improved.",
        question: "Extract key metrics and trends as JSON",
        output_format: "json",
        language: "en",
      },
      client
    );
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.key_metrics).toEqual(["revenue", "profit"]);
  });

  it("hy3_plan_knowledge_graph returns graph JSON", async () => {
    const textFile = join(tempDir, "text.txt");
    await writeFile(textFile, "Alice works with Bob. Bob manages Charlie.");
    const client = createMockClient(
      JSON.stringify({
        nodes: [{ id: "Alice", group: 1 }, { id: "Bob", group: 1 }, { id: "Charlie", group: 2 }],
        links: [{ source: "Alice", target: "Bob", relation: "works with" }],
      })
    );
    const result = await handleToolCall(
      "hy3_plan_knowledge_graph",
      { file_path: textFile, language: "en" },
      client
    );
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.nodes).toHaveLength(3);
  });

  it("hy3_render_knowledge_graph renders SVG", async () => {
    const nodes = JSON.stringify([{ id: "Alice", group: 1 }, { id: "Bob", group: 2 }]);
    const links = JSON.stringify([{ source: "Alice", target: "Bob", relation: "works with" }]);
    const result = await handleToolCall(
      "hy3_render_knowledge_graph",
      { nodes, links, output_format: "svg" },
      {} as Hy3Client
    );
    expect(result.content[0].text).toContain("knowledge graph");
    expect(result.content[0].text).toContain("2 entities");
  });

  it("hy3_render_knowledge_graph renders PNG", async () => {
    const nodes = JSON.stringify([{ id: "Alice", group: 1 }, { id: "Bob", group: 2 }]);
    const links = JSON.stringify([{ source: "Alice", target: "Bob", relation: "works with" }]);
    const result = await handleToolCall(
      "hy3_render_knowledge_graph",
      { nodes, links, output_format: "png" },
      {} as Hy3Client
    );
    expect(result.content[0].text).toContain("PNG");
  });

  it("hy3_plan_wordcloud returns word JSON", async () => {
    const textFile = join(tempDir, "text.txt");
    await writeFile(textFile, "data visualization charts data charts");
    const client = createMockClient(JSON.stringify([{ word: "data", weight: 100 }, { word: "charts", weight: 80 }]));
    const result = await handleToolCall(
      "hy3_plan_wordcloud",
      { file_path: textFile, language: "en" },
      client
    );
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.words).toHaveLength(2);
  });

  it("hy3_render_wordcloud renders SVG from explicit words", async () => {
    const words = JSON.stringify([{ word: "data", weight: 100 }, { word: "charts", weight: 80 }]);
    const result = await handleToolCall(
      "hy3_render_wordcloud",
      { words, output_format: "svg", language: "en" },
      {} as Hy3Client
    );
    expect(result.content[0].text).toContain("word cloud");
    expect(result.content[0].text).toContain("2 keywords");
  });

  it("hy3_render_wordcloud renders HTML from raw text", async () => {
    const result = await handleToolCall(
      "hy3_render_wordcloud",
      { text: "alpha beta gamma alpha beta alpha", output_format: "html", language: "en" },
      {} as Hy3Client
    );
    expect(result.content[0].text).toContain("HTML");
  });

  it("hy3_plan_chart returns a chart config JSON", async () => {
    const client = createMockClient(
      JSON.stringify({
        chart_type: "bar",
        x_column: "month",
        y_column: "sales",
        title: "Monthly Sales",
      })
    );
    const result = await handleToolCall(
      "hy3_plan_chart",
      { data: '[{"month":"Jan","sales":100},{"month":"Feb","sales":150}]', question: "Recommend a chart", language: "en" },
      client
    );
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.chart_type).toBe("bar");
    expect(parsed.x_column).toBe("month");
  });

  it("hy3_plan_wordcloud returns words JSON", async () => {
    const client = createMockClient(JSON.stringify([{ word: "data", weight: 100 }, { word: "charts", weight: 80 }]));
    const result = await handleToolCall(
      "hy3_plan_wordcloud",
      { text: "data visualization charts data", language: "en" },
      client
    );
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.words).toHaveLength(2);
  });

  it("hy3_plan_knowledge_graph returns graph JSON", async () => {
    const client = createMockClient(
      JSON.stringify({
        nodes: [{ id: "A", group: 1 }, { id: "B", group: 2 }],
        links: [{ source: "A", target: "B", relation: "links" }],
      })
    );
    const result = await handleToolCall(
      "hy3_plan_knowledge_graph",
      { text: "A links B", language: "en" },
      client
    );
    const parsed = JSON.parse(result.content[0].text);
    expect(parsed.nodes).toHaveLength(2);
    expect(parsed.links).toHaveLength(1);
  });

  it("hy3_render_chart validates required columns", async () => {
    const dataFile = join(tempDir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\n");

    await expect(
      handleToolCall(
        "hy3_render_chart",
        { file_path: dataFile, chart_type: "bubble", x_column: "month", y_column: "sales", language: "en" },
        {} as Hy3Client
      )
    ).rejects.toThrow("size_column");
  });

  it("hy3_render_chart applies overrides", async () => {
    const dataFile = join(tempDir, "data.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\n");

    const result = await handleToolCall(
      "hy3_render_chart",
      {
        file_path: dataFile,
        chart_type: "bar",
        x_column: "month",
        y_column: "sales",
        overrides: JSON.stringify({ title: { text: "Overridden Title" } }),
        language: "en",
      },
      {} as Hy3Client
    );

    const match = result.content[0].text.match(/File path: (.+)/);
    expect(match).toBeTruthy();
    const svgPath = match![1].trim();
    const svg = await readFile(svgPath, "utf-8");
    expect(svg).toContain("Overridden Title");
  });
});
