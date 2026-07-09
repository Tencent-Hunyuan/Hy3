import { readFile } from "fs/promises";
import * as XLSX from "xlsx";
import PDFParser from "pdf2json";
import mammoth from "mammoth";
import { DataTable } from "./utils.js";

export type DocumentType = "txt" | "pdf" | "docx" | "xlsx" | "csv" | "json";

export function detectDocumentType(filePath: string): DocumentType {
  const ext = filePath.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "pdf":
      return "pdf";
    case "docx":
      return "docx";
    case "xlsx":
    case "xls":
      return "xlsx";
    case "csv":
      return "csv";
    case "json":
    case "jsonl":
      return "json";
    default:
      return "txt";
  }
}

export async function extractTextFromDocument(filePath: string): Promise<string> {
  const type = detectDocumentType(filePath);

  switch (type) {
    case "pdf":
      return extractPdfText(filePath);
    case "docx":
      return extractDocxText(filePath);
    case "xlsx":
      return extractXlsxText(filePath);
    case "txt":
    case "csv":
    case "json":
    default:
      return readFile(filePath, "utf-8");
  }
}

async function extractPdfText(filePath: string): Promise<string> {
  const parser = new PDFParser();

  return new Promise((resolve, reject) => {
    parser.on("pdfParser_dataReady", (data) => {
      const pages = data.Pages || [];
      const text = pages
        .map((page) =>
          (page.Texts || [])
            .map((textItem) => (textItem.R || []).map((run) => decodeURIComponent(run.T)).join(""))
            .join(" ")
        )
        .join("\n");
      resolve(text);
    });

    parser.on("pdfParser_dataError", (err) => {
      reject(err);
    });

    parser.loadPDF(filePath);
  });
}

async function extractDocxText(filePath: string): Promise<string> {
  const result = await mammoth.extractRawText({ path: filePath });
  return result.value;
}

async function extractXlsxText(filePath: string): Promise<string> {
  const buffer = await readFile(filePath);
  const workbook = XLSX.read(buffer, { type: "buffer" });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  return XLSX.utils.sheet_to_csv(sheet);
}

export function parseXlsx(buffer: Buffer): DataTable {
  const workbook = XLSX.read(buffer, { type: "buffer" });
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const json = XLSX.utils.sheet_to_json<Record<string, unknown>>(sheet, { defval: "" });

  if (json.length === 0) {
    return { columns: [], rows: [], raw: "" };
  }

  const columns = Array.from(new Set(json.flatMap((row) => Object.keys(row))));
  const rows = json.map((row: Record<string, unknown>) => {
    const record: Record<string, string | number> = {};
    columns.forEach((col) => {
      const value = row[col];
      if (typeof value === "number") record[col] = value;
      else record[col] = value == null ? "" : String(value);
    });
    return record;
  });

  return { columns, rows, raw: XLSX.utils.sheet_to_csv(sheet) };
}
