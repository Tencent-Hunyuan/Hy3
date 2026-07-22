import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";


test("研究证据漂移定位证据断裂并导出 Markdown", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "分析研究证据漂移" }).click();

  await expect(page.getByRole("heading", { name: "step-006-unsupported-causal-leap" })).toBeVisible();
  await expect(page.getByTestId("timeline-step-step-006-unsupported-causal-leap")).toHaveAttribute(
    "data-divergence",
    "true",
  );
  await expect(page.getByText("获取并导入直接相关的因果来源", { exact: false })).toBeVisible();

  await page.getByRole("button", { name: "ev-source-a" }).first().click();
  await expect(page.getByRole("heading", { name: "ev-source-a" })).toBeVisible();
  await expect(page.getByText("没有检验政策是否导致", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "关闭证据" }).click();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出 Markdown" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("轨迹复盘报告.md");
  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const exported = await readFile(downloadPath!, "utf-8");
  expect(exported).toContain("step-006-unsupported-causal-leap");
  expect(exported).toContain("## 最小重放计划");
});


test("the evidence and replay workflow remains usable at a narrow mobile viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");

  await page.getByRole("button", { name: "分析研究证据漂移" }).click();
  await expect(page.getByRole("heading", { name: "step-006-unsupported-causal-leap" })).toBeVisible();
  await page.getByRole("button", { name: "ev-source-a" }).first().click();
  await expect(page.getByRole("heading", { name: "ev-source-a" })).toBeVisible();

  const horizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth,
  );
  expect(horizontalOverflow).toBeLessThanOrEqual(1);
  const drawer = await page.locator(".evidence-drawer").boundingBox();
  expect(drawer).not.toBeNull();
  expect(drawer!.x).toBeGreaterThanOrEqual(0);
  expect(drawer!.width).toBeLessThanOrEqual(390);
});
