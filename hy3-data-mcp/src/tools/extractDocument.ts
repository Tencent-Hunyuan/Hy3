import { z } from "zod";
import { detectDocumentType, extractTextFromDocument } from "../documents.js";
import type { ProgressReporter } from "./index.js";

export const extractDocumentDefinition = {
  name: "hy3_extract_document",
  description:
    "Extract raw text and metadata from PDF, Word (DOCX), TXT, CSV, JSON, or XLSX files. Does NOT use LLM. For unstructured documents (PDF/DOCX/TXT), pass the returned text to hy3_analyze_text. For structured files (CSV/JSON/XLSX), prefer hy3_data_* tools directly.",
  inputSchema: {
    type: "object" as const,
    properties: {
      file_path: {
        type: "string",
        description: "Path to a PDF, DOCX, TXT, CSV, JSON or XLSX file.",
      },
    },
    required: ["file_path"],
  },
};

export const extractDocumentSchema = z.object({
  file_path: z.string().min(1),
});

export async function runExtractDocument(
  args: unknown,
  _client: unknown,
  onProgress?: ProgressReporter
): Promise<{ content: Array<{ type: "text"; text: string }> }> {
  const { file_path } = extractDocumentSchema.parse(args);

  await onProgress?.(10, 100);
  const documentType = detectDocumentType(file_path);
  await onProgress?.(40, 100);

  const text = await extractTextFromDocument(file_path);
  await onProgress?.(80, 100);

  if (!text.trim()) {
    throw new Error("No text could be extracted from the document.");
  }

  const isStructured = documentType === "csv" || documentType === "json" || documentType === "xlsx";

  const result = {
    document_type: documentType,
    text,
    has_structured_data: isStructured,
    structured_hint: isStructured
      ? "This file already contains structured data. Prefer hy3_data_visualize, hy3_data_insight, hy3_data_report, or hy3_data_dashboard for analysis and visualization."
      : "This is an unstructured document. Pass the extracted text to hy3_analyze_text for summarization, extraction, or structured data conversion.",
  };

  await onProgress?.(100, 100);
  return { content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }] };
}
