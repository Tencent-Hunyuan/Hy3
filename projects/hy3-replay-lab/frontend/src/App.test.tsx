import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";


const fixtureList = [
  {
    fixture_id: "coding-loop",
    title: "编程循环",
    description: "修复缺陷时，智能体重复了只处理边缘的修改。",
    domain: "代码任务",
  },
  {
    fixture_id: "research-grounding",
    title: "研究证据漂移",
    description: "研究智能体逐步失去证据约束。",
    domain: "研究任务",
  },
];

const analysisResponse = {
  report: {
    schema_version: "1.0",
    report_id: "report_test",
    fixture_id: "coding-loop",
    task: {
      title: "修复 slugify 的连续分隔符",
      description: "在不削弱测试的前提下修复回归。",
    },
    criteria: [
      {
        criterion_id: "criterion-collapse",
        title: "折叠连续分隔符",
        description: "将每组连续分隔符折叠为一个。",
        priority: "must",
      },
    ],
    timeline: [
      {
        step_id: "step-005-test-feedback",
        sequence: 5,
        kind: "tool_result",
        summary: "新的连续分隔符测试失败。",
        details: "预期只保留一个连字符。",
        status: "failed",
        criterion_ids: ["criterion-collapse"],
        evidence_ids: ["ev-repeat-failure"],
      },
      {
        step_id: "step-006-repeat-patch",
        sequence: 6,
        kind: "decision",
        summary: "在矛盾反馈后重复了仅修剪边缘的修改。",
        details: "失败所揭示的约束被忽略。",
        status: "warning",
        criterion_ids: ["criterion-collapse"],
        evidence_ids: ["ev-repeat-failure"],
      },
    ],
    evidence: [
      {
        evidence_id: "ev-repeat-failure",
        step_id: "step-005-test-feedback",
        kind: "test_result",
        source_label: "合成测试输出",
        content: "预期 alpha-beta，实际得到 alpha--beta。",
      },
    ],
    coverage: [
      {
        criterion_id: "criterion-collapse",
        status: "violated",
        supporting_step_ids: ["step-005-test-feedback", "step-006-repeat-patch"],
        evidence_ids: ["ev-repeat-failure"],
        explanation: "该约束仍未满足。",
      },
    ],
    finding: {
      severity: "high",
      category: "constraint_omission",
      first_divergence_step_id: "step-006-repeat-patch",
      impact_step_ids: [],
      explanation: "智能体在测试证据与当前方向矛盾后仍重复了同一修改。",
      evidence_ids: ["ev-repeat-failure"],
      hypotheses: [],
    },
    replay_plan: {
      preserved_step_ids: ["step-005-test-feedback"],
      rerun_from_step_id: "step-006-repeat-patch",
      rerun_step_ids: ["step-006-repeat-patch"],
      actions: [
        {
          order: 1,
          action: "实现连续分隔符折叠。",
          evidence_ids: ["ev-repeat-failure"],
          validation_gate: {
            description: "连续分隔符回归测试通过。",
            criterion_ids: ["criterion-collapse"],
            evidence_ids: ["ev-repeat-failure"],
          },
        },
      ],
      stop_conditions: [
        {
          description: "回归测试通过后停止。",
          criterion_ids: ["criterion-collapse"],
          evidence_ids: ["ev-repeat-failure"],
        },
      ],
      prohibited_actions: [
        {
          action: "跳过测试。",
          reason: "该测试对应已确认的验收约束。",
          evidence_ids: ["ev-repeat-failure"],
        },
      ],
    },
    metadata: {
      provider: "static-fixture",
      model: "offline-fixture",
      mode: "fake",
    },
  },
  exports: {
    json: "{\n  \"report_id\": \"report_test\"\n}\n",
    markdown: "# 轨迹复盘报告\n\n## 最小重放计划\n",
  },
};

describe("ReplayLab vertical slice", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("loads coding-loop, highlights divergence, shows replay plan, and exports JSON", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/fixtures") {
        return new Response(JSON.stringify(fixtureList), { status: 200 });
      }
      if (url === "/api/health") {
        return new Response(
          JSON.stringify({ status: "ok", live_provider_configured: true }),
          { status: 200 },
        );
      }
      if (url === "/api/analyze" && init?.method === "POST") {
        return new Response(JSON.stringify(analysisResponse), { status: 200 });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:replay-report"),
      revokeObjectURL: vi.fn(),
    });
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Hy3 轨迹复盘台" })).toBeVisible();
    fireEvent.click(await screen.findByRole("button", { name: "分析编程循环" }));

    expect(await screen.findByText("在矛盾反馈后重复了仅修剪边缘的修改。")).toBeVisible();
    expect(screen.getByTestId("timeline-step-step-006-repeat-patch")).toHaveAttribute(
      "data-divergence",
      "true",
    );
    expect(screen.getByText("实现连续分隔符折叠。")).toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: "导出 JSON" }));
    await waitFor(() => expect(clickSpy).toHaveBeenCalledOnce());
  });

  it("lets a configured user explicitly select live Hy3 without sending a key", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/fixtures") {
        return new Response(JSON.stringify(fixtureList), { status: 200 });
      }
      if (url === "/api/health") {
        return new Response(
          JSON.stringify({ status: "ok", live_provider_configured: true }),
          { status: 200 },
        );
      }
      if (url === "/api/analyze" && init?.method === "POST") {
        expect(init.body).toBe(
          JSON.stringify({ fixture_id: "coding-loop", provider: "hy3" }),
        );
        expect(String(init.body)).not.toMatch(/api[_-]?key|authorization|bearer/i);
        return new Response(
          JSON.stringify({
            ...analysisResponse,
            report: {
              ...analysisResponse.report,
              metadata: {
                provider: "tencent-tokenhub",
                model: "hy3",
                mode: "live",
                latency_ms: 1234,
                prompt_tokens: 100,
                completion_tokens: 50,
                total_tokens: 150,
                request_attempts: 1,
              },
            },
          }),
          { status: 200 },
        );
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "在线 Hy3" }));
    fireEvent.click(screen.getByRole("button", { name: "分析编程循环" }));

    expect(await screen.findByText(/1,234 毫秒/)).toBeVisible();
    expect(screen.getByText(/150 个令牌/)).toBeVisible();
  });

  it("imports an allowed local file and analyzes its normalized task through live Hy3", async () => {
    const importedTask = {
      schema_version: "1.0",
      fixture_id: null,
      task: {
        title: "导入轨迹",
        description: "一条公开的合成自定义轨迹。",
      },
      criteria: analysisResponse.report.criteria,
      trace: analysisResponse.report.timeline,
      evidence: analysisResponse.report.evidence,
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/fixtures") {
        return new Response(JSON.stringify(fixtureList), { status: 200 });
      }
      if (url === "/api/health") {
        return new Response(
          JSON.stringify({ status: "ok", live_provider_configured: true }),
          { status: 200 },
        );
      }
      if (url === "/api/import") {
        const body = JSON.parse(String(init?.body));
        expect(body).toMatchObject({
          filename: "custom.json",
          content_type: "application/json",
        });
        return new Response(JSON.stringify(importedTask), { status: 200 });
      }
      if (url === "/api/analyze") {
        const body = JSON.parse(String(init?.body));
        expect(body).toEqual({ task: importedTask, provider: "hy3" });
        expect(String(init?.body)).not.toMatch(/authorization|bearer|api[_-]?key/i);
        return new Response(JSON.stringify(analysisResponse), { status: 200 });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const file = new File([JSON.stringify(importedTask)], "custom.json", {
      type: "application/json",
    });
    Object.defineProperty(file, "text", {
      value: vi.fn(async () => JSON.stringify(importedTask)),
    });

    render(<App />);

    fireEvent.change(
      await screen.findByLabelText("导入 JSON、Markdown 或文本轨迹"),
      { target: { files: [file] } },
    );
    fireEvent.click(await screen.findByRole("button", { name: "分析导入轨迹" }));

    expect(await screen.findByText("在矛盾反馈后重复了仅修剪边缘的修改。")).toBeVisible();
    expect(screen.getByText("custom.json")).toBeVisible();
  });

  it("surfaces bounded 429 guidance and retries the selected fixture", async () => {
    let analysisCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/fixtures") {
        return new Response(JSON.stringify(fixtureList), { status: 200 });
      }
      if (url === "/api/health") {
        return new Response(
          JSON.stringify({ status: "ok", live_provider_configured: true }),
          { status: 200 },
        );
      }
      if (url === "/api/analyze") {
        analysisCalls += 1;
        if (analysisCalls === 1) {
          return new Response(
            JSON.stringify({ detail: "Hy3 is temporarily rate-limited" }),
            { status: 429, headers: { "Retry-After": "7" } },
          );
        }
        return new Response(JSON.stringify(analysisResponse), { status: 200 });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "在线 Hy3" }));
    fireEvent.click(screen.getByRole("button", { name: "分析编程循环" }));

    expect(await screen.findByText("Hy3 请求受限，请在 7 秒后重试。")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "重试" }));
    expect(await screen.findByText("在矛盾反馈后重复了仅修剪边缘的修改。")).toBeVisible();
    expect(analysisCalls).toBe(2);
  });

  it("stops waiting for an in-flight analysis without leaving a stale error", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
        const url = String(input);
        if (url === "/api/fixtures") {
          return new Response(JSON.stringify(fixtureList), { status: 200 });
        }
        if (url === "/api/health") {
          return new Response(
            JSON.stringify({ status: "ok", live_provider_configured: false }),
            { status: 200 },
          );
        }
        if (url === "/api/analyze") {
          return await new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener("abort", () => {
              reject(new DOMException("cancelled", "AbortError"));
            });
          });
        }
        throw new Error(`Unexpected request: ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "分析编程循环" }));
    fireEvent.click(await screen.findByRole("button", { name: "停止等待" }));

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "停止等待" })).not.toBeInTheDocument();
    });
    expect(screen.queryByText("分析已安全停止")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "分析编程循环" })).toBeEnabled();
  });
});
