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

function maybeNumber(value: string): string | number {
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
