import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Evidence } from "../types";
import EvidenceDrawer from "./EvidenceDrawer";


const evidence: Evidence = {
  evidence_id: "ev-public-result",
  step_id: "step-003-check",
  kind: "test_result",
  source_label: "公开合成测试",
  content: "预期 alpha-beta，实际得到 alpha--beta。",
};


describe("EvidenceDrawer accessibility", () => {
  afterEach(cleanup);

  it("announces a dialog, focuses close, handles Escape, and restores focus", async () => {
    const onClose = vi.fn();
    const { rerender } = render(
      <>
        <button type="button">打开证据</button>
        <EvidenceDrawer evidence={null} onClose={onClose} />
      </>,
    );
    const trigger = screen.getByRole("button", { name: "打开证据" });
    trigger.focus();

    rerender(
      <>
        <button type="button">打开证据</button>
        <EvidenceDrawer evidence={evidence} onClose={onClose} />
      </>,
    );

    expect(screen.getByRole("dialog", { name: "ev-public-result" })).toBeVisible();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "关闭证据" })).toHaveFocus();
    });
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();

    rerender(
      <>
        <button type="button">打开证据</button>
        <EvidenceDrawer evidence={null} onClose={onClose} />
      </>,
    );
    expect(trigger).toHaveFocus();
  });
});
