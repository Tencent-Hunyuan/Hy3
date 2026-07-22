import type {
  AnalysisProvider,
  AnalysisResponse,
  FixtureSummary,
  HealthResponse,
  TaskSpec,
} from "./types";


export class ReplayApiError extends Error {
  readonly status: number;
  readonly retryAfterSeconds: number | null;

  constructor(message: string, status: number, retryAfterSeconds: number | null = null) {
    super(message);
    this.name = "ReplayApiError";
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

export async function listFixtures(signal?: AbortSignal): Promise<FixtureSummary[]> {
  const response = await fetch("/api/fixtures", { signal });
  if (!response.ok) {
    throw await apiError(response, "无法加载内置轨迹。");
  }
  return (await response.json()) as FixtureSummary[];
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch("/api/health", { signal });
  if (!response.ok) {
    throw await apiError(response, "无法读取本地模型状态。");
  }
  return (await response.json()) as HealthResponse;
}

export async function analyzeFixture(
  fixtureId: string,
  provider: AnalysisProvider,
  signal?: AbortSignal,
): Promise<AnalysisResponse> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fixture_id: fixtureId, provider }),
    signal,
  });
  if (!response.ok) {
    throw await apiError(response, "无法分析这条轨迹。");
  }
  return (await response.json()) as AnalysisResponse;
}

export async function importTaskFile(
  filename: string,
  contentType: string,
  content: string,
  signal?: AbortSignal,
): Promise<TaskSpec> {
  const response = await fetch("/api/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, content_type: contentType, content }),
    signal,
  });
  if (!response.ok) {
    throw await apiError(response, "导入轨迹未通过校验。");
  }
  return (await response.json()) as TaskSpec;
}

export async function analyzeImportedTask(
  task: TaskSpec,
  signal?: AbortSignal,
): Promise<AnalysisResponse> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, provider: "hy3" }),
    signal,
  });
  if (!response.ok) {
    throw await apiError(response, "无法分析导入轨迹。");
  }
  return (await response.json()) as AnalysisResponse;
}

async function apiError(response: Response, fallback: string): Promise<ReplayApiError> {
  let message = fallback;
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.length <= 240) {
      message = payload.detail;
    }
  } catch {
    // A bounded generic message is safer than echoing an arbitrary response body.
  }
  const retryAfter = response.headers.get("Retry-After");
  const parsedRetryAfter = retryAfter === null ? null : Number.parseInt(retryAfter, 10);
  return new ReplayApiError(
    message,
    response.status,
    Number.isFinite(parsedRetryAfter) ? parsedRetryAfter : null,
  );
}
