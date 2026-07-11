import { z } from "zod";
import { Hy3Client, UsageInfo } from "./client.js";

export interface AskJsonOptions {
  maxRetries?: number;
  retryDelayMs?: number;
  includeUsage?: boolean;
  signal?: AbortSignal;
  onToken?: (token: string) => void;
}

export interface AskJsonResult<T> {
  data: T;
  usage?: UsageInfo;
  repaired: boolean;
}

export function safeJsonParse(text: string): unknown {
  const trimmed = text.trim();

  // If the input already looks like a JSON object/array, parse it directly first.
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try {
      return JSON.parse(trimmed);
    } catch {
      // fall through to extraction heuristics
    }
  }

  // Try to extract JSON from markdown code fence
  const fenceMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
  if (fenceMatch) {
    try {
      return JSON.parse(fenceMatch[1]);
    } catch {
      // fall through
    }
  }

  // Try to find the first JSON object/array embedded in surrounding text
  const arrayMatch = trimmed.match(/(\[[\s\S]*\])/);
  if (arrayMatch) {
    try {
      return JSON.parse(arrayMatch[1]);
    } catch {
      // fall through
    }
  }
  const objectMatch = trimmed.match(/(\{[\s\S]*\})/);
  if (objectMatch) {
    try {
      return JSON.parse(objectMatch[1]);
    } catch {
      // fall through
    }
  }

  return JSON.parse(trimmed);
}

export async function askHy3Json<T>(
  client: Hy3Client,
  system: string,
  user: string,
  schema: z.ZodType<T>,
  options: AskJsonOptions = {}
): Promise<AskJsonResult<T>> {
  const { maxRetries = 2, retryDelayMs = 500, includeUsage = false, signal, onToken } = options;

  let lastError: Error | undefined;
  let totalUsage: UsageInfo | undefined;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await client.chatWithUsage(
        [
          { role: "system", content: system },
          { role: "user", content: attempt > 0 ? `${user}\n\n注意：之前返回的内容不是合法 JSON，请直接输出可解析的 JSON，不要包含任何额外说明。` : user },
        ],
        { signal, onToken }
      );

      if (includeUsage && result.usage) {
        totalUsage = addUsage(totalUsage, result.usage);
      }

      const parsed = safeJsonParse(result.content);
      const validated = schema.parse(parsed);
      return { data: validated, usage: totalUsage, repaired: attempt > 0 };
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      if (attempt < maxRetries) {
        await delay(retryDelayMs * (attempt + 1));
      }
    }
  }

  throw lastError ?? new Error("Failed to get valid JSON from Hy3 after retries");
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function addUsage(a: UsageInfo | undefined, b: UsageInfo): UsageInfo {
  return {
    prompt_tokens: (a?.prompt_tokens ?? 0) + (b.prompt_tokens ?? 0),
    completion_tokens: (a?.completion_tokens ?? 0) + (b.completion_tokens ?? 0),
    total_tokens: (a?.total_tokens ?? 0) + (b.total_tokens ?? 0),
  };
}

export function formatUsage(usage: UsageInfo | undefined): string {
  if (!usage) return "";
  return `Tokens: ${usage.total_tokens ?? "?"} (prompt ${usage.prompt_tokens ?? "?"}, completion ${usage.completion_tokens ?? "?"})`;
}
