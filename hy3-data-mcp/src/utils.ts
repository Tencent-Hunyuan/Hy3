import { readFile } from "fs/promises";
import { mkdir, writeFile } from "fs/promises";
import { dirname, resolve } from "path";
import Papa from "papaparse";
import { Hy3Client } from "./client.js";
import { parseXlsx } from "./documents.js";
import { getTheme } from "./viz/themes.js";
import type { Theme } from "./viz/themes.js";

export interface DataTable {
  columns: string[];
  rows: Record<string, string | number>[];
  raw: string;
}

export interface ColorOverrideArgs {
  background_color?: string;
  text_color?: string;
  axis_color?: string;
  split_line_color?: string;
  palette?: string[];
  primary_color?: string;
}

export function buildThemeOverrides(
  args: ColorOverrideArgs,
  baseThemeName?: string
): Partial<Omit<Theme, "name">> {
  const overrides: Partial<Omit<Theme, "name">> = {};
  if (args.background_color) overrides.backgroundColor = args.background_color;
  if (args.text_color) overrides.textColor = args.text_color;
  if (args.axis_color) overrides.axisColor = args.axis_color;
  if (args.split_line_color) overrides.splitLineColor = args.split_line_color;
  if (args.palette && args.palette.length > 0) {
    overrides.palette = args.palette;
  } else if (args.primary_color) {
    const base = getTheme(baseThemeName).palette;
    overrides.palette = [args.primary_color, ...base.slice(1)];
  }
  return overrides;
}

export async function readLocalFile(filePath: string): Promise<string> {
  try {
    return await readFile(filePath, "utf-8");
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to read file '${filePath}': ${message}`);
  }
}

export async function loadDataTable(filePath: string): Promise<DataTable> {
  const ext = filePath.split(".").pop()?.toLowerCase();

  if (ext === "xlsx" || ext === "xls") {
    const buffer = await readFile(filePath);
    return parseXlsx(buffer);
  }

  const raw = await readLocalFile(filePath);
  return parseData(raw, ext);
}

/**
 * Read a plain text file (txt, md, log, etc.) without parsing it as structured data.
 */
export async function readTextFile(filePath: string): Promise<string> {
  return readLocalFile(filePath);
}

export function parseInlineData(data: string): DataTable {
  const parsed = JSON.parse(data);
  const rows = Array.isArray(parsed) ? parsed : [parsed];
  const columns = rows.length > 0 ? Array.from(new Set(rows.flatMap(Object.keys))) : [];
  return { columns, rows: rows.map(normalizeRow(columns)), raw: data };
}

export function parseData(raw: string, ext?: string): DataTable {
  const trimmed = raw.trim();
  const lowerExt = ext?.toLowerCase();

  if (
    lowerExt === ".json" ||
    lowerExt === ".jsonl" ||
    trimmed.startsWith("[") ||
    trimmed.startsWith("{")
  ) {
    try {
      const parsed = JSON.parse(trimmed);
      const rows = Array.isArray(parsed) ? parsed : [parsed];
      const columns = rows.length > 0 ? Array.from(new Set(rows.flatMap(Object.keys))) : [];
      return { columns, rows: rows.map(normalizeRow(columns)), raw };
    } catch {
      // fall through to CSV
    }
  }

  const result = Papa.parse<string[]>(trimmed, { skipEmptyLines: true });
  if (result.data.length === 0) {
    return { columns: [], rows: [], raw };
  }
  const [header, ...body] = result.data;
  const columns = header;
  const rows = body.map((row) => {
    const record: Record<string, string | number> = {};
    columns.forEach((col, i) => {
      const value = row[i] ?? "";
      record[col] = maybeNumber(value);
    });
    return record;
  });
  return { columns, rows, raw };
}

function normalizeRow(columns: string[]) {
  return (row: Record<string, unknown>): Record<string, string | number> => {
    const record: Record<string, string | number> = {};
    columns.forEach((col) => {
      const value = row[col];
      if (typeof value === "number") record[col] = value;
      else record[col] = value == null ? "" : String(value);
    });
    return record;
  };
}

export function maybeNumber(value: string): string | number {
  const trimmed = value.trim();
  if (trimmed === "") return "";
  const num = Number(trimmed);
  return Number.isFinite(num) ? num : trimmed;
}

export function sampleText(raw: string, maxChars = 12000): string {
  return raw.slice(0, maxChars);
}

export function tableSummary(table: DataTable): string {
  const columns = table.columns.join(", ");
  const preview = table.rows
    .slice(0, 5)
    .map((row) => JSON.stringify(row))
    .join("\n");
  return `Columns: ${columns}\nRows: ${table.rows.length}\nPreview:\n${preview}`;
}

const ID_COLUMN_PATTERN = /\b(id|key|index|no|num|timestamp|date|time|score|rating|price|age|amount|count|qty|quantity)\b|_id$|_key$/i;
const TEXT_COLUMN_PATTERN = /text|content|comment|review|description|title|摘要|描述|内容|评论|标题/i;

/**
 * Heuristically select the column most likely to contain free text.
 * Excludes obvious ID / numeric metadata columns and prefers columns
 * whose names hint at text content and whose values are long strings.
 */
export function selectTextColumn(
  columns: string[],
  rows: Record<string, string | number>[]
): string | null {
  if (columns.length === 0) return null;

  const candidates = columns
    .filter((col) => !ID_COLUMN_PATTERN.test(col))
    .map((col) => {
      const values = rows.map((row) => String(row[col] ?? ""));
      const lengths = values.map((v) => v.length);
      const avgLen = lengths.reduce((a, b) => a + b, 0) / lengths.length;
      const maxLen = Math.max(...lengths);
      const isTextName = TEXT_COLUMN_PATTERN.test(col) ? 1 : 0;
      return { col, avgLen, maxLen, isTextName };
    });

  if (candidates.length === 0) {
    return columns[0];
  }

  const hasTextLike = candidates.some((c) => c.isTextName === 1 || c.avgLen > 3);
  if (!hasTextLike) {
    return columns[0];
  }

  candidates.sort((a, b) => {
    if (b.isTextName !== a.isTextName) return b.isTextName - a.isTextName;
    if (b.avgLen !== a.avgLen) return b.avgLen - a.avgLen;
    return b.maxLen - a.maxLen;
  });

  return candidates[0].col;
}

export async function askHy3(
  client: Hy3Client,
  system: string,
  user: string,
  signal?: AbortSignal,
  onToken?: (token: string) => void
): Promise<string> {
  return client.chat(
    [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
    { signal, onToken }
  );
}

export function loadOutputDir(): string {
  return process.env.HY3_OUTPUT_DIR
    ? resolve(process.env.HY3_OUTPUT_DIR)
    : resolve(process.cwd(), "hy3-data-output");
}

export function detectLanguage(text: string): "zh" | "en" {
  if (!text) return "en";
  const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length;
  const totalChars = text.replace(/\s/g, "").length || 1;
  return chineseChars / totalChars > 0.1 ? "zh" : "en";
}

export function resolveLanguage(
  language: "zh" | "en" | "auto" | undefined,
  ...samples: (string | undefined)[]
): "zh" | "en" {
  if (language && language !== "auto") return language;
  const combined = samples.filter(Boolean).join(" ");
  return detectLanguage(combined);
}

export async function writeOutputFile(
  relativePath: string,
  content: string | Buffer
): Promise<string> {
  const outputDir = loadOutputDir();
  const filePath = resolve(outputDir, relativePath);
  await mkdir(dirname(filePath), { recursive: true });
  await writeFile(filePath, content);
  return filePath;
}

export function sanitizeFilename(name: string): string {
  return name
    .replace(/[\\/:*?"<>|]/g, "_")
    .replace(/[^a-zA-Z0-9\u4e00-\u9fa5_.-]/g, "_");
}

export function resolveOutputFilename(
  provided: string | undefined,
  defaultName: string,
  ext: string
): string {
  if (provided && provided.trim()) {
    let name = provided.trim();
    const suffix = `.${ext}`;
    if (name.toLowerCase().endsWith(suffix.toLowerCase())) {
      name = name.slice(0, -suffix.length);
    }
    name = sanitizeFilename(name);
    if (!name) name = defaultName;
    return `${name}.${ext}`;
  }
  return `${defaultName}.${ext}`;
}

export interface InputDataArgs {
  data?: string;
  data_file_path?: string;
  file_path?: string;
}

/**
 * Load a DataTable from one of the supported input forms:
 * - `data`: inline JSON array string
 * - `data_file_path`: path to CSV/JSON/XLSX containing structured data
 * - `file_path`: alias for backward compatibility / general file input
 */
export async function loadInputData(args: InputDataArgs): Promise<DataTable> {
  if (args.data) {
    return parseInlineData(args.data);
  }
  const path = args.data_file_path || args.file_path;
  if (!path) {
    throw new Error("One of data, data_file_path, or file_path is required");
  }
  return loadDataTable(path);
}

/**
 * Extract text content from a file regardless of whether it is plain text or structured.
 * For structured files, returns the raw file content.
 */
export async function loadInputText(args: { text?: string; file_path?: string }): Promise<string> {
  if (args.text) return args.text;
  if (args.file_path) return readTextFile(args.file_path);
  throw new Error("One of text or file_path is required");
}
