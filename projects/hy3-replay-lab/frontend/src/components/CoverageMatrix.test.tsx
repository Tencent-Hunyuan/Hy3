import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import CoverageMatrix from "./CoverageMatrix";


describe("CoverageMatrix", () => {
  afterEach(cleanup);

  it("gives each constraint and evidence action a contextual accessible name", () => {
    const onEvidenceSelect = vi.fn();
    render(
      <CoverageMatrix
        coverage={[
          {
            criterion_id: "criterion-grounding",
            status: "violated",
            supporting_step_ids: ["step-003-claim"],
            evidence_ids: ["ev-source-a"],
            explanation: "该结论超出了导入来源的支持范围。",
          },
        ]}
        criteria={[
          {
            criterion_id: "criterion-grounding",
            title: "为每条结论提供依据",
            description: "每条结论都需要直接证据。",
            priority: "must",
          },
        ]}
        onEvidenceSelect={onEvidenceSelect}
      />,
    );

    expect(
      screen.getByRole("article", {
        name: "为每条结论提供依据：约束未满足",
      }),
    ).toBeVisible();
    expect(screen.getByRole("status", { name: "未满足" })).toBeVisible();
    fireEvent.click(
      screen.getByRole("button", {
        name: "查看“为每条结论提供依据”的证据 ev-source-a",
      }),
    );
    expect(onEvidenceSelect).toHaveBeenCalledWith("ev-source-a");
  });
});
