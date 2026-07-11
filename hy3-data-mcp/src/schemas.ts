import { z } from "zod";

export const THEME_NAMES = [
  "light",
  "dark",
  "colorful",
  "minimal",
  "professional",
  "premium",
  "retro",
  "science",
  "nature",
] as const;

export const themeSchema = (defaultTheme: (typeof THEME_NAMES)[number] = "nature") =>
  z.enum(THEME_NAMES).default(defaultTheme);

export const languageSchema = z.enum(["zh", "en", "auto"]).default("auto");

export const outputFilenameSchema = z.string().optional();

export const dimensionsSchema = (widthDefault = 800, heightDefault = 500) => ({
  width: z.number().int().min(200).max(2000).default(widthDefault),
  height: z.number().int().min(200).max(2000).default(heightDefault),
});

export const colorOverrideSchema = z.object({
  background_color: z.string().optional(),
  text_color: z.string().optional(),
  axis_color: z.string().optional(),
  split_line_color: z.string().optional(),
  palette: z.array(z.string()).optional(),
  primary_color: z.string().optional(),
});

export const dataInputShape = {
  data: z.string().optional(),
  data_file_path: z.string().optional(),
  file_path: z.string().optional(),
};

export const dataInputRefinement = (schema: z.ZodObject<typeof dataInputShape>) =>
  schema.refine(
    (args) => Boolean(args.data?.trim()) || Boolean(args.data_file_path?.trim()) || Boolean(args.file_path?.trim()),
    {
      message: "One of data, data_file_path, or file_path is required",
    }
  );

export const rawThemeProperty = (defaultTheme: string, description?: string) => ({
  type: "string" as const,
  enum: [...THEME_NAMES],
  default: defaultTheme,
  description:
    description ?? "Color theme for charts.",
});

export const rawLanguageProperty = (description?: string) => ({
  type: "string" as const,
  enum: ["zh", "en", "auto"],
  default: "auto",
  description: description ?? "Language of the output. 'auto' detects from input.",
});

export const rawOutputFilenameProperty = (description?: string) => ({
  type: "string" as const,
  description: description ?? "Optional custom output file name (without extension).",
});

export const rawDimensionsProperties = (widthDefault = 800, heightDefault = 500) => ({
  width: { type: "number" as const, description: "Chart width in pixels.", default: widthDefault },
  height: { type: "number" as const, description: "Chart height in pixels.", default: heightDefault },
});

export const rawColorOverrideProperties = {
  background_color: { type: "string" as const, description: "Optional chart background color hex." },
  text_color: { type: "string" as const, description: "Optional chart text color hex." },
  axis_color: { type: "string" as const, description: "Optional chart axis color hex." },
  split_line_color: { type: "string" as const, description: "Optional chart grid line color hex." },
  palette: { type: "array" as const, items: { type: "string" }, description: "Optional custom color palette as an array of hex colors." },
  primary_color: { type: "string" as const, description: "Optional primary chart color hex." },
};

export const rawDataInputProperties = {
  data: { type: "string" as const, description: "Inline structured data as a JSON array string." },
  data_file_path: { type: "string" as const, description: "Path to a CSV/JSON/XLSX file." },
  file_path: { type: "string" as const, description: "Alias for data_file_path." },
};
