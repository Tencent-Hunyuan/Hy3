import { z } from "zod";
import { detectDocumentType, extractTablesFromDocx, extractTablesFromPdf, extractTextFromDocument } from "../documents.js";
import { loadDataTable } from "../utils.js";
import type { ProgressReporter } from "./index.js";

export const extractDocumentDefinition = {
  name: "hy3_extract_document",
  description:
    "Extract raw text and metadata from PDF, Word (DOCX), TXT, CSV, JSON, or XLSX files. Does NOT use LLM. For unstructured documents (PDF/DOCX/TXT), pass the returned text to hy3_analyze. For structured files (CSV/JSON/XLSX), prefer hy3_render_chart, hy3_analyze, or hy3_analyze_report.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to a PDF, DOCX, TXT, CSV, JSON or XLSX file.",
      },
      extract_tables: {
        type: "boolean",
        description: "For PDF/DOCX, attempt to extract tables as JSON arrays. If not feasible for PDF, returns empty tables with a note.",
        default: false,
      },
      return_data: {
        type: "boolean",
        description: "For CSV/JSON/XLSX, return parsed rows/columns in the data field.",
        default: false,
      },
      max_text_length: {
        type: "number",
        description: "Maximum number of characters to return in the text field.",
        default: 100000,
      },
    },
    required: ["file_path"],
  },
};

export const extractDocumentSchema = z.object({
  file_path: z.string().min(1),
  extract_tables: z.boolean().default(false),
  return_data: z.boolean().default(false),
  max_text_length: z.number().int().min(1).default(100000),
});

export async function runExtractDocument(
  args: unknown,
  _client: unknown,
  onProgress?: ProgressReporter
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { file_path, extract_tables, return_data, max_text_length } = extractDocumentSchema.parse(args);

  await onProgress?.(10, 100);
  const documentType = detectDocumentType(file_path);
  await onProgress?.(40, 100);

  let text = await extractTextFromDocument(file_path);
  await onProgress?.(80, 100);

  const isStructured = documentType === "csv" || documentType === "json" || documentType === "xlsx";

  const result: Record<string, unknown> = {
    document_type: documentType,
    text: text.slice(0, max_text_length),
    has_structured_data: isStructured,
    structured_hint: isStructured
      ? "This file contains structured data. Use hy3_render_chart, hy3_analyze, or hy3_analyze_report."
      : "This is an unstructured document. Pass the extracted text to hy3_analyze for summarization, extraction, or structured data conversion.",
  };

  if (extract_tables) {
    if (documentType === "docx") {
      try {
        const tables = await extractTablesFromDocx(file_path);
        result.tables = tables.map((t) => ({ columns: t.columns, rows: t.rows }));
        result.tables_note = tables.length > 0 ? undefined : "No tables detected in the DOCX.";
      } catch {
        result.tables = [];
        result.tables_note = "DOCX table extraction failed. Tables will be returned as empty arrays.";
      }
    } else if (documentType === "pdf") {
      try {
        const tables = await extractTablesFromPdf(file_path);
        result.tables = tables.map((t) => ({ columns: t.columns, rows: t.rows }));
        result.tables_note = tables.length > 0 ? undefined : "No tables detected in the PDF.";
      } catch {
        result.tables = [];
        result.tables_note = "PDF table extraction failed. Tables will be returned as empty arrays.";
      }
    } else {
      result.tables = [];
      result.tables_note = "Table extraction is only relevant for PDF/DOCX documents.";
    }
  }

  if (return_data && isStructured) {
    try {
      const table = await loadDataTable(file_path);
      result.data = {
        columns: table.columns,
        rows: table.rows,
      };
    } catch {
      result.data = { columns: [], rows: [], note: "Could not parse structured data." };
    }
  }

  await onProgress?.(100, 100);
  return { content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }] };
}
