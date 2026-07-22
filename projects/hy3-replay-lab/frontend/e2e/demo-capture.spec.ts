import path from "node:path";

import { expect, test } from "@playwright/test";


test("截取两条公开离线复盘流程用于中文界面演示", async ({ page }) => {
  test.skip(
    process.env.REPLAYLAB_CAPTURE_DEMO !== "1",
    "Set REPLAYLAB_CAPTURE_DEMO=1 to regenerate the actual-UI demo frames.",
  );
  const frame = (name: string) =>
    path.resolve("..", "docs", "demo", "frames", `${name}.png`);

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "选择一个复盘场景" })).toBeVisible();
  await page.screenshot({ path: frame("01-case-picker"), fullPage: false });

  await page.getByRole("button", { name: "分析编程循环" }).click();
  const codingFinding = page.getByRole("heading", { name: "step-006-repeat-patch" });
  await expect(codingFinding).toBeVisible();
  await codingFinding.scrollIntoViewIfNeeded();
  await page.screenshot({ path: frame("02-coding-divergence"), fullPage: false });
  await page.getByRole("button", { name: "ev-repeat-failure" }).first().click();
  await expect(page.getByRole("dialog", { name: "ev-repeat-failure" })).toBeVisible();
  await page.screenshot({ path: frame("03-coding-evidence"), fullPage: false });
  await page.getByRole("button", { name: "关闭证据" }).click();
  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出 JSON" }).click();
  await jsonDownload;

  await page.getByRole("button", { name: "分析研究证据漂移" }).click();
  const researchFinding = page.getByRole("heading", {
    name: "step-006-unsupported-causal-leap",
  });
  await expect(researchFinding).toBeVisible();
  await researchFinding.scrollIntoViewIfNeeded();
  await page.screenshot({ path: frame("04-research-divergence"), fullPage: false });
  await page.getByRole("button", { name: "ev-source-a" }).first().click();
  await expect(page.getByRole("dialog", { name: "ev-source-a" })).toBeVisible();
  await page.screenshot({ path: frame("05-research-evidence"), fullPage: false });
  await page.getByRole("button", { name: "关闭证据" }).click();
  const markdownDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出 Markdown" }).click();
  await markdownDownload;
});
