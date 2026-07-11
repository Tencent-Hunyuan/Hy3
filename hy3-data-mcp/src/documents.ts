import { readFile } from "fs/promises";
import exceljs from "exceljs";
import type { Worksheet } from "exceljs";
import PDFParser from "pdf2json";

const Workbook = exceljs.Workbook;
import * as mammoth from "mammoth";
import { DataTable, maybeNumber } from "./utils.js";

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

async function extractDocxText(filePath: string): Promise<string> {
  const result = await mammoth.extractRawText({ path: filePath });
  return result.value;
}

function formatCellValue(value: unknown): string {
  if (value == null) return "";
  if (value instanceof Date) return value.toISOString().split("T")[0];
  if (
    typeof value === "object" &&
    "richText" in value &&
    Array.isArray((value as { richText?: Array<{ text?: unknown }> }).richText)
  ) {
    return (value as { richText: Array<{ text?: unknown }> }).richText
      .map((part) => String(part.text ?? ""))
      .join("");
  }
  return String(value);
}

function escapeCsvCell(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function worksheetToCsv(worksheet: Worksheet): string {
  const rows: string[][] = [];
  worksheet.eachRow((row) => {
    const cells: string[] = [];
    row.eachCell({ includeEmpty: true }, (cell) => {
      cells.push(formatCellValue(cell.value));
    });
    rows.push(cells);
  });
  return rows.map((row) => row.map(escapeCsvCell).join(",")).join("\n");
}

async function extractXlsxText(filePath: string): Promise<string> {
  const buffer = await readFile(filePath);
  const workbook = new Workbook();
  await workbook.xlsx.load(buffer as any);
  const worksheet = workbook.worksheets[0];
  if (!worksheet) return "";
  return worksheetToCsv(worksheet);
}

export async function extractTablesFromDocx(filePath: string): Promise<DataTable[]> {
  const result = await (mammoth as any).convertToHtml({ path: filePath });
  const html = result.value;
  const tables: DataTable[] = [];

  const tableRegex = /<table[^>]*>(.*?)<\/table>/gis;
  const rowRegex = /<tr[^>]*>(.*?)<\/tr>/gis;
  const cellRegex = /<t[dh][^>]*>(.*?)<\/t[dh]>/gis;

  for (const tableMatch of html.matchAll(tableRegex)) {
    const rows: string[][] = [];
    for (const rowMatch of tableMatch[1].matchAll(rowRegex)) {
      const cells: string[] = [];
      for (const cellMatch of rowMatch[1].matchAll(cellRegex)) {
        cells.push(stripHtmlTags(cellMatch[1]).trim());
      }
      if (cells.length > 0) rows.push(cells);
    }
    if (rows.length >= 2) {
      const header = rows[0];
      const body = rows.slice(1);
      tables.push({
        columns: header,
        rows: body.map((row) => {
          const record: Record<string, string | number> = {};
          header.forEach((col, idx) => {
            record[col] = maybeNumber(row[idx] ?? "");
          });
          return record;
        }),
        raw: JSON.stringify(body),
      });
    }
  }

  return tables;
}

function stripHtmlTags(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

export async function extractTablesFromPdf(filePath: string): Promise<DataTable[]> {
  const data = await parsePdfRaw(filePath);
  const tables: DataTable[] = [];

  for (const page of data.Pages || []) {
    const items: Array<{ x: number; y: number; text: string }> = (page.Texts || [])
      .map(
        (textItem: any): { x: number; y: number; text: string } => ({
          x: textItem.x as number,
          y: textItem.y as number,
          text: (textItem.R || [])
            .map((run: any) => {
              try {
                return decodeURIComponent(run.T);
              } catch {
                return run.T;
              }
            })
            .join(""),
        })
      )
      .filter((item: { x: number; y: number; text: string }) => item.text.trim().length > 0);

    if (items.length === 0) continue;

    // Group items into rows by rounded y coordinate.
    const rowsByY = new Map<number, Array<{ x: number; text: string }>>();
    for (const item of items) {
      const y = Math.round(item.y);
      if (!rowsByY.has(y)) rowsByY.set(y, []);
      rowsByY.get(y)!.push({ x: item.x, text: item.text });
    }

    const rowGroups = Array.from(rowsByY.entries())
      .map(([y, rowItems]) => ({ y, items: rowItems.sort((a, b) => a.x - b.x) }))
      .sort((a, b) => a.y - b.y);

    // Detect table runs: consecutive rows with the same number of items (>=2).
    // We infer columns independently for each run so stray one-off text items
    // (like a page title sitting between table columns) do not create empty columns.
    let i = 0;
    while (i < rowGroups.length) {
      const firstCount = rowGroups[i].items.length;
      if (firstCount < 2) {
        i++;
        continue;
      }

      let j = i + 1;
      while (j < rowGroups.length && rowGroups[j].items.length === firstCount) {
        j++;
      }

      const run = rowGroups.slice(i, j);
      if (run.length < 2) {
        i++;
        continue;
      }

      const colCenters = clusterValues(run.flatMap((r) => r.items.map((item) => item.x)), 2.5);
      if (colCenters.length !== firstCount) {
        i++;
        continue;
      }

      const cellRows = run.map((row) => {
        const cells = Array(colCenters.length).fill("");
        for (const item of row.items) {
          let bestIdx = 0;
          let bestDist = Infinity;
          for (let c = 0; c < colCenters.length; c++) {
            const dist = Math.abs(item.x - colCenters[c]);
            if (dist < bestDist) {
              bestDist = dist;
              bestIdx = c;
            }
          }
          if (bestDist <= 4) {
            cells[bestIdx] = cells[bestIdx] ? `${cells[bestIdx]} ${item.text}` : item.text;
          }
        }
        return cells.map((c: string) => c.trim());
      });

      const header = cellRows[0];
      const body = cellRows.slice(1);
      const rows = body.map((row) => {
        const record: Record<string, string | number> = {};
        header.forEach((col, idx) => {
          const val = row[idx] ?? "";
          record[col] = maybeNumber(val);
        });
        return record;
      });
      tables.push({ columns: header, rows, raw: JSON.stringify(rows) });
      i = j;
    }
  }

  return tables;
}

function clusterValues(values: number[], tolerance: number): number[] {
  if (values.length === 0) return [];
  const sorted = [...values].sort((a, b) => a - b);
  const centers: number[] = [sorted[0]];
  const counts: number[] = [1];

  for (let i = 1; i < sorted.length; i++) {
    const v = sorted[i];
    const lastIdx = centers.length - 1;
    if (Math.abs(v - centers[lastIdx]) <= tolerance) {
      centers[lastIdx] = (centers[lastIdx] * counts[lastIdx] + v) / (counts[lastIdx] + 1);
      counts[lastIdx]++;
    } else {
      centers.push(v);
      counts.push(1);
    }
  }

  return centers.sort((a, b) => a - b);
}

async function parsePdfRaw(filePath: string): Promise<any> {
  const parser = new PDFParser();
  return new Promise((resolve, reject) => {
    parser.on("pdfParser_dataReady", (data) => resolve(data));
    parser.on("pdfParser_dataError", (err) => reject(err));
    parser.loadPDF(filePath);
  });
}

async function extractPdfText(filePath: string): Promise<string> {
  const data = await parsePdfRaw(filePath);

  const pages = data.Pages || [];
  const text = pages
    .map((page: any) =>
      (page.Texts || [])
        .map((textItem: any) =>
          (textItem.R || [])
            .map((run: any) => {
              try {
                return decodeURIComponent(run.T);
              } catch {
                return run.T;
              }
            })
            .join("")
        )
        .join(" ")
    )
    .join("\n");
  return text;
}

export async function parseXlsx(buffer: Buffer): Promise<DataTable> {
  const workbook = new Workbook();
  await workbook.xlsx.load(buffer as any);
  const worksheet = workbook.worksheets[0];

  if (!worksheet || worksheet.rowCount === 0) {
    return { columns: [], rows: [], raw: "" };
  }

  const columnCount = worksheet.getRow(1).cellCount;
  const rawRows: unknown[][] = [];
  worksheet.eachRow((row) => {
    const rowValues: unknown[] = [];
    for (let i = 1; i <= columnCount; i++) {
      rowValues.push(row.getCell(i).value);
    }
    rawRows.push(rowValues);
  });

  if (rawRows.length === 0) {
    return { columns: [], rows: [], raw: "" };
  }

  const columns = rawRows[0].map((value) => String(value));
  const rows = rawRows.slice(1).map((rowValues) => {
    const record: Record<string, string | number> = {};
    columns.forEach((col, idx) => {
      const value = rowValues[idx];
      if (typeof value === "number") {
        record[col] = value;
      } else if (value instanceof Date) {
        record[col] = value.toISOString().split("T")[0];
      } else {
        record[col] = value == null ? "" : String(value);
      }
    });
    return record;
  });

  return {
    columns,
    rows,
    raw: rawRows
      .map((row) => row.map((v) => escapeCsvCell(formatCellValue(v))).join(","))
      .join("\n"),
  };
}
