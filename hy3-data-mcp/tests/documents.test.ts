import { describe, it, expect } from "vitest";
import { join } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";
import { Workbook } from "exceljs";
import {
  detectDocumentType,
  extractTablesFromDocx,
  extractTablesFromPdf,
  extractTextFromDocument,
  parseXlsx,
} from "../src/documents.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const sampleDir = join(__dirname, "..", "sample_data");

describe("detectDocumentType", () => {
  it.each([
    ["file.pdf", "pdf"],
    ["file.docx", "docx"],
    ["file.xlsx", "xlsx"],
    ["file.xls", "xlsx"],
    ["file.csv", "csv"],
    ["file.json", "json"],
    ["file.jsonl", "json"],
    ["file.txt", "txt"],
    ["file.unknown", "txt"],
    ["FILE.PDF", "pdf"],
  ])("detects %s as %s", (file, expected) => {
    expect(detectDocumentType(file)).toBe(expected);
  });
});

describe("extractTextFromDocument", () => {
  it("extracts text from a DOCX file", async () => {
    const text = await extractTextFromDocument(join(sampleDir, "report.docx"));
    expect(text).toContain("Q1-Q4 Sales Report");
    expect(text).toContain("Quarterly Performance");
    expect(text).toContain("Q4");
  });

  it("extracts text from a PDF file", async () => {
    const text = await extractTextFromDocument(join(sampleDir, "report.pdf"));
    expect(text).toContain("Q1-Q4 Sales Report");
    expect(text).toContain("Total annual revenue reached");
  });

  it("reads plain text files as-is", async () => {
    const text = await extractTextFromDocument(join(sampleDir, "article.txt"));
    expect(text.length).toBeGreaterThan(0);
  });
});

describe("extractTablesFromPdf", () => {
  it("extracts the quarterly performance table from report.pdf", async () => {
    const tables = await extractTablesFromPdf(join(sampleDir, "report.pdf"));
    expect(tables.length).toBeGreaterThanOrEqual(1);
    const table = tables[0];
    expect(table.columns).toEqual(["Quarter", "Revenue ($)", "Units Sold"]);
    expect(table.rows).toHaveLength(4);
    expect(table.rows[0]).toMatchObject({ Quarter: "Q1", "Revenue ($)": "120,000", "Units Sold": "3,400" });
    expect(table.rows[3]).toMatchObject({ Quarter: "Q4", "Revenue ($)": "152,000", "Units Sold": "4,100" });
  });
});

describe("extractTablesFromDocx", () => {
  it("extracts the quarterly performance table from report.docx", async () => {
    const tables = await extractTablesFromDocx(join(sampleDir, "report.docx"));
    expect(tables.length).toBeGreaterThanOrEqual(1);
    const table = tables[0];
    expect(table.columns).toEqual(["Quarter", "Revenue ($)", "Units Sold"]);
    expect(table.rows).toHaveLength(4);
    expect(table.rows[0]).toMatchObject({ Quarter: "Q1", "Revenue ($)": "120,000", "Units Sold": "3,400" });
    expect(table.rows[3]).toMatchObject({ Quarter: "Q4", "Revenue ($)": "152,000", "Units Sold": "4,100" });
  });
});

describe("parseXlsx", () => {
  it("parses an XLSX buffer into a DataTable", async () => {
    const workbook = new Workbook();
    const sheet = workbook.addWorksheet("Sheet1");
    sheet.addRows([
      ["Month", "Sales"],
      ["Jan", 100],
      ["Feb", 150],
    ]);
    const buffer = await workbook.xlsx.writeBuffer();

    const table = await parseXlsx(buffer as Buffer);
    expect(table.columns).toEqual(["Month", "Sales"]);
    expect(table.rows).toHaveLength(2);
    expect(table.rows[0]).toEqual({ Month: "Jan", Sales: 100 });
    expect(table.rows[1]).toEqual({ Month: "Feb", Sales: 150 });
  });

  it("returns empty table for an empty workbook", async () => {
    const workbook = new Workbook();
    workbook.addWorksheet("Sheet1");
    const buffer = await workbook.xlsx.writeBuffer();

    const table = await parseXlsx(buffer as Buffer);
    expect(table.columns).toEqual([]);
    expect(table.rows).toEqual([]);
  });
});
