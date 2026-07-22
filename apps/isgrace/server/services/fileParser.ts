import fs from 'fs-extra';
import { createRequire } from 'module';
import mammoth from 'mammoth';

// pdf-parse is CJS-only; its ESM wrapper has no default export — load via createRequire.
// v2's API is class-based (new PDFParse({ data }).getText()), not the v1 function-export shape.
const _require = createRequire(import.meta.url);
interface PDFParseInstance {
  getText(): Promise<{ text: string }>;
  destroy(): Promise<void>;
}
const { PDFParse } = _require('pdf-parse') as {
  PDFParse: new (opts: { data: Buffer }) => PDFParseInstance;
};

// Any single Hy3 call is bounded by its 262,144-token context regardless of
// this constant — large materials are handled by chunking calls (see
// dispatchGrace.ts's runExtractModules), not by keeping stored content small.
// This is purely a backstop against pathological files (corrupted PDFs, OCR
// garbage), not a functional ceiling — real materials should never hit it.
const MAX_CHARS = 3_000_000;

function truncate(text: string, label: string): string {
  if (text.length <= MAX_CHARS) return text;
  return text.slice(0, MAX_CHARS) + `\n\n[… ${label} content truncated at ${MAX_CHARS.toLocaleString()} characters]`;
}

/** pdf-parse v2's getText() inserts "-- N of M --" page-boundary markers between pages — strip them, keeping a paragraph break. */
function stripPageMarkers(text: string): string {
  return text.replace(/\n*--\s*\d+\s*of\s*\d+\s*--\n*/g, '\n\n');
}

export async function parsePDF(filePath: string): Promise<string> {
  const buffer = await fs.readFile(filePath);
  const parser = new PDFParse({ data: buffer });
  try {
    const result = await parser.getText();
    const text = stripPageMarkers(result.text.replace(/\r\n/g, '\n')).replace(/\n{3,}/g, '\n\n').trim();
    return truncate(text, 'PDF');
  } finally {
    await parser.destroy();
  }
}

export async function parseDOCX(filePath: string): Promise<string> {
  const result = await mammoth.extractRawText({ path: filePath });
  const text = result.value.replace(/\n{3,}/g, '\n\n').trim();
  return truncate(text, 'DOCX');
}

export async function parseTXT(filePath: string): Promise<string> {
  const text = (await fs.readFile(filePath, 'utf-8')).trim();
  return truncate(text, 'text');
}
