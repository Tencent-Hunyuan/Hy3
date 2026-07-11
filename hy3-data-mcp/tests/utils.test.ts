import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtemp, writeFile, rm } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { Workbook } from "exceljs";
import {
  parseData,
  loadDataTable,
  detectLanguage,
  resolveLanguage,
  buildThemeOverrides,
  tableSummary,
  loadOutputDir,
  writeOutputFile,
  selectTextColumn,
  resolveOutputFilename,
  validateDataTable,
  assertColumnsExist,
} from "../src/utils.js";

describe("parseData", () => {
  it("parses CSV data with header and rows", () => {
    const table = parseData("name,value\nA,10\nB,20", "csv");
    expect(table.columns).toEqual(["name", "value"]);
    expect(table.rows).toEqual([
      { name: "A", value: 10 },
      { name: "B", value: 20 },
    ]);
  });

  it("parses JSON array data", () => {
    const table = parseData('[{"x":1,"y":2},{"x":3,"y":4}]', "json");
    expect(table.columns).toEqual(["x", "y"]);
    expect(table.rows).toHaveLength(2);
  });

  it("parses JSON object data as a single row", () => {
    const table = parseData('{"product":"A","sales":100}', "json");
    expect(table.columns).toEqual(["product", "sales"]);
    expect(table.rows).toEqual([{ product: "A", sales: 100 }]);
  });

  it("returns empty table for empty input", () => {
    const table = parseData("");
    expect(table.columns).toEqual([]);
    expect(table.rows).toEqual([]);
  });
});

describe("loadDataTable", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "hy3-utils-"));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it("loads a CSV file", async () => {
    const file = join(tempDir, "data.csv");
    await writeFile(file, "a,b\n1,2\n3,4");
    const table = await loadDataTable(file);
    expect(table.columns).toEqual(["a", "b"]);
    expect(table.rows).toHaveLength(2);
  });

  it("loads an XLSX file", async () => {
    const file = join(tempDir, "data.xlsx");
    const workbook = new Workbook();
    const sheet = workbook.addWorksheet("Sheet1");
    sheet.addRows([
      ["Month", "Sales"],
      ["Jan", 100],
    ]);
    await writeFile(file, await workbook.xlsx.writeBuffer());
    const table = await loadDataTable(file);
    expect(table.columns).toEqual(["Month", "Sales"]);
    expect(table.rows).toHaveLength(1);
  });
});

describe("language helpers", () => {
  it("detects Chinese text", () => {
    expect(detectLanguage("这是中文")).toBe("zh");
  });

  it("detects English text", () => {
    expect(detectLanguage("This is English")).toBe("en");
  });

  it("defaults to English for empty text", () => {
    expect(detectLanguage("")).toBe("en");
  });

  it("resolveLanguage returns explicit language", () => {
    expect(resolveLanguage("zh", "hello")).toBe("zh");
  });

  it("resolveLanguage auto-detects from samples", () => {
    expect(resolveLanguage("auto", "这是中文")).toBe("zh");
    expect(resolveLanguage("auto", "English text")).toBe("en");
  });
});

describe("buildThemeOverrides", () => {
  it("applies palette override", () => {
    const overrides = buildThemeOverrides({ palette: ["#ff0000", "#00ff00"] }, "nature");
    expect(overrides.palette).toEqual(["#ff0000", "#00ff00"]);
  });

  it("applies primary color to the start of the base palette", () => {
    const overrides = buildThemeOverrides({ primary_color: "#123456" }, "nature");
    expect(overrides.palette?.[0]).toBe("#123456");
    expect(overrides.palette?.length).toBeGreaterThan(1);
  });

  it("applies background and text colors", () => {
    const overrides = buildThemeOverrides(
      { background_color: "#000000", text_color: "#ffffff" },
      "nature"
    );
    expect(overrides.backgroundColor).toBe("#000000");
    expect(overrides.textColor).toBe("#ffffff");
  });
});

describe("tableSummary", () => {
  it("returns columns, row count, and preview", () => {
    const summary = tableSummary({
      columns: ["a", "b"],
      rows: [{ a: 1, b: 2 }, { a: 3, b: 4 }],
      raw: "",
    });
    expect(summary).toContain("Columns: a, b");
    expect(summary).toContain("Rows: 2");
    expect(summary).toContain('{"a":1,"b":2}');
  });
});

describe("loadOutputDir", () => {
  const originalEnv = process.env.HY3_OUTPUT_DIR;

  afterEach(() => {
    process.env.HY3_OUTPUT_DIR = originalEnv;
  });

  it("uses the environment variable when set", () => {
    const envDir = join(process.cwd(), "custom-output-env");
    process.env.HY3_OUTPUT_DIR = envDir;
    expect(loadOutputDir()).toBe(envDir);
  });

  it("falls back to ./hy3-data-output", () => {
    delete process.env.HY3_OUTPUT_DIR;
    expect(loadOutputDir()).toBe(join(process.cwd(), "hy3-data-output"));
  });
});

describe("writeOutputFile", () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(tmpdir(), "hy3-output-"));
    process.env.HY3_OUTPUT_DIR = tempDir;
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
    delete process.env.HY3_OUTPUT_DIR;
  });

  it("writes content to the output directory and returns the absolute path", async () => {
    const filePath = await writeOutputFile("charts/test.svg", "<svg></svg>");
    const now = new Date();
    const dateFolder = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
    expect(filePath).toBe(join(tempDir, dateFolder, "svg", "test.svg"));
    const content = await (await import("fs/promises")).readFile(filePath, "utf-8");
    expect(content).toBe("<svg></svg>");
  });
});

describe("validateDataTable", () => {
  it("throws for empty columns", () => {
    expect(() => validateDataTable({ columns: [], rows: [], raw: "" })).toThrow("no columns");
  });

  it("throws for empty rows", () => {
    expect(() => validateDataTable({ columns: ["a"], rows: [], raw: "a" })).toThrow("no rows");
  });

  it("throws when required columns are missing", () => {
    expect(() =>
      validateDataTable({ columns: ["a", "b"], rows: [{ a: 1, b: 2 }], raw: "" }, ["c"])
    ).toThrow("Missing required column");
  });

  it("passes for valid table", () => {
    expect(() =>
      validateDataTable({ columns: ["a", "b"], rows: [{ a: 1, b: 2 }], raw: "" }, ["a"])
    ).not.toThrow();
  });
});

describe("assertColumnsExist", () => {
  it("throws with available columns when a column is missing", () => {
    const table = { columns: ["month", "sales"], rows: [{ month: "Jan", sales: 100 }], raw: "" };
    expect(() => assertColumnsExist(table, ["month", "profit"], "Chart")).toThrow("profit");
    expect(() => assertColumnsExist(table, ["month", "profit"], "Chart")).toThrow("month, sales");
  });
});

describe("resolveOutputFilename", () => {
  it("uses provided name and extension", () => {
    expect(resolveOutputFilename("my-chart", "default", "svg")).toBe("my-chart.svg");
  });

  it("strips matching extension from provided name", () => {
    expect(resolveOutputFilename("my-chart.svg", "default", "svg")).toBe("my-chart.svg");
  });

  it("sanitizes unsafe characters", () => {
    expect(resolveOutputFilename("a/b:c?d", "default", "png")).toBe("a_b_c_d.png");
  });

  it("falls back to default when name is empty", () => {
    expect(resolveOutputFilename("", "default_123", "html")).toBe("default_123.html");
  });
});

describe("selectTextColumn", () => {
  it("prefers a long text column over an ID column", () => {
    const column = selectTextColumn(
      ["review_id", "comment", "rating"],
      [
        { review_id: 1, comment: "产品质量非常好，物流也很快，下次还会购买。", rating: 5 },
        { review_id: 2, comment: "包装有点破损，但是产品本身没问题。", rating: 3 },
      ]
    );
    expect(column).toBe("comment");
  });

  it("excludes ID-like columns even if their names contain text keywords", () => {
    const column = selectTextColumn(
      ["review_id", "user_id", "text"],
      [
        { review_id: 1, user_id: "u1", text: "这是一条真实的用户评论内容" },
        { review_id: 2, user_id: "u2", text: "另一条评论内容" },
      ]
    );
    expect(column).toBe("text");
  });

  it("falls back to the first column when all columns look like IDs", () => {
    const column = selectTextColumn(
      ["id", "key", "idx"],
      [
        { id: 1, key: "a", idx: 0 },
        { id: 2, key: "b", idx: 1 },
      ]
    );
    expect(column).toBe("id");
  });

  it("returns null for an empty column list", () => {
    expect(selectTextColumn([], [])).toBeNull();
  });
});
