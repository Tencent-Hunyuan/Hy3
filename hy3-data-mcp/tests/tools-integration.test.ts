import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mkdtemp, writeFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { handleToolCall } from "../src/tools/index.js";
import { Hy3Client } from "../src/client.js";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const sampleDir = join(__dirname, "..", "sample_data");

function createMockClient(response: string | string[] = "mocked response") {
  const fn = vi.fn();
  if (Array.isArray(response)) {
    for (const r of response) {
      fn.mockResolvedValueOnce(r);
    }
  } else {
    fn.mockResolvedValue(response);
  }
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

  it("hy3_data_dashboard generates an HTML dashboard", async () => {
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
      "hy3_data_dashboard",
      { file_paths: [dataFile], title: "Sales Dashboard", output_format: "html", language: "en", layout: "grid" },
      client,
      progress
    );

    expect(result.content[0].text).toContain("Sales Dashboard");
    expect(result.content[0].text).toContain("HTML");
    expect(progress).toHaveBeenCalled();
  });

  it("hy3_data_dashboard generates a PNG dashboard", async () => {
    const dataFile = join(tempDir, "sales.csv");
    await writeFile(dataFile, "month,sales\nJan,100\nFeb,150\nMar,120\n");

    const client = createMockClient(
      JSON.stringify({
        title: "PNG Dashboard",
        charts: [{ file_index: 0, chart_type: "line", x_column: "month", y_column: "sales", title: "Sales" }],
      })
    );
    const result = await handleToolCall(
      "hy3_data_dashboard",
      { file_paths: [dataFile], output_format: "png", language: "en", layout: "rows" },
      client
    );

    expect(result.content[0].text).toContain("PNG");
  });

  it("hy3_document_summary returns text for a DOCX", async () => {
    const docx = join(sampleDir, "report.docx");
    const client = createMockClient("Summary text");
    const result = await handleToolCall(
      "hy3_document_summary",
      { file_path: docx, question: "Summarize", output_format: "text", language: "en" },
      client
    );
    expect(result.content[0].text).toBe("Summary text");
  });

  it("hy3_document_summary generates HTML for a PDF", async () => {
    const pdf = join(sampleDir, "report.pdf");
    const client = createMockClient("PDF summary");
    const result = await handleToolCall(
      "hy3_document_summary",
      { file_path: pdf, question: "Summarize", output_format: "html", language: "en" },
      client
    );
    expect(result.content[0].text).toContain("HTML");
    expect(result.content[0].text).toContain("File path:");
  });

  it("hy3_document_visualize extracts data from a DOCX and renders SVG", async () => {
    const docx = join(sampleDir, "report.docx");
    const client = createMockClient([
      JSON.stringify({
        columns: ["Quarter", "Revenue"],
        rows: [{ Quarter: "Q1", Revenue: 120000 }],
      }),
      JSON.stringify({ x_column: "Quarter", y_column: "Revenue", title: "Quarterly Revenue" }),
    ]);
    const result = await handleToolCall(
      "hy3_document_visualize",
      { file_path: docx, chart_type: "bar", output_format: "svg", language: "en" },
      client
    );
    expect(result.content[0].text).toContain("SVG");
    expect(result.content[0].text).toContain("File path:");
  });

  it("hy3_document_visualize renders a dashboard from structured CSV", async () => {
    const csv = join(tempDir, "data.csv");
    await writeFile(csv, "a,b\n1,2\n3,4\n");
    const client = createMockClient(JSON.stringify({ x_column: "a", y_column: "b", title: "Chart" }));
    const result = await handleToolCall(
      "hy3_document_visualize",
      { file_path: csv, chart_type: "dashboard", output_format: "html", language: "en" },
      client
    );
    expect(result.content[0].text).toContain("dashboard");
  });

  it("hy3_knowledge_graph renders SVG with extracted entities", async () => {
    const textFile = join(tempDir, "text.txt");
    await writeFile(textFile, "Alice works with Bob. Bob manages Charlie.");
    const client = createMockClient(
      JSON.stringify({
        nodes: [{ id: "Alice", group: 1 }, { id: "Bob", group: 1 }, { id: "Charlie", group: 2 }],
        links: [{ source: "Alice", target: "Bob", relation: "works with" }],
      })
    );
    const result = await handleToolCall(
      "hy3_knowledge_graph",
      { file_path: textFile, output_format: "svg", language: "en" },
      client
    );
    expect(result.content[0].text).toContain("knowledge graph");
    expect(result.content[0].text).toContain("3 entities");
  });

  it("hy3_knowledge_graph renders PNG", async () => {
    const textFile = join(tempDir, "text.txt");
    await writeFile(textFile, "Alice works with Bob.");
    const client = createMockClient(
      JSON.stringify({
        nodes: [{ id: "Alice", group: 1 }, { id: "Bob", group: 2 }],
        links: [{ source: "Alice", target: "Bob", relation: "works with" }],
      })
    );
    const result = await handleToolCall(
      "hy3_knowledge_graph",
      { file_path: textFile, output_format: "png", language: "en" },
      client
    );
    expect(result.content[0].text).toContain("PNG");
  });

  it("hy3_wordcloud renders SVG with mocked keywords", async () => {
    const textFile = join(tempDir, "text.txt");
    await writeFile(textFile, "data visualization charts data charts");
    const client = createMockClient(JSON.stringify([{ word: "data", weight: 100 }, { word: "charts", weight: 80 }]));
    const result = await handleToolCall(
      "hy3_wordcloud",
      { file_path: textFile, output_format: "svg", language: "en" },
      client
    );
    expect(result.content[0].text).toContain("word cloud");
    expect(result.content[0].text).toContain("2 keywords");
  });

  it("hy3_wordcloud renders HTML and falls back on invalid Hy3 response", async () => {
    const textFile = join(tempDir, "text.txt");
    await writeFile(textFile, "alpha beta gamma alpha beta alpha");
    const client = createMockClient("not json");
    const result = await handleToolCall(
      "hy3_wordcloud",
      { file_path: textFile, output_format: "html", language: "en" },
      client
    );
    expect(result.content[0].text).toContain("HTML");
  });
});
