import { readFile } from "node:fs/promises";
import path from "node:path";

import { expect, test } from "@playwright/test";


test("录制两条真实 Hy3 在线复盘流程", async ({ page }) => {
  test.skip(
    process.env.REPLAYLAB_CAPTURE_LIVE_DEMO !== "1",
    "Set REPLAYLAB_CAPTURE_LIVE_DEMO=1 to regenerate the live Hy3 demo frames.",
  );
  test.setTimeout(150_000);
  const frame = (name: string) =>
    path.resolve("..", "docs", "demo", "live-frames", `${name}.png`);

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "选择一个复盘场景" })).toBeVisible();
  const liveMode = page.getByRole("button", { name: "在线 Hy3" });
  await expect(liveMode).toBeEnabled();
  await liveMode.click();
  await expect(liveMode).toHaveAttribute("aria-pressed", "true");
  await page.screenshot({ path: frame("01-case-picker"), fullPage: false });

  const startedAt = Date.now();
  await page.getByRole("button", { name: "分析编程循环" }).click();
  const codingFinding = page.getByRole("heading", { name: "step-006-repeat-patch" });
  await expect(codingFinding).toBeVisible({ timeout: 90_000 });
  await expect(page.locator(".mode-badge")).toHaveText("在线 Hy3");
  await codingFinding.scrollIntoViewIfNeeded();
  await page.screenshot({ path: frame("02-coding-divergence"), fullPage: false });
  await page.getByRole("button", { name: "ev-repeat-failure" }).first().click();
  await expect(page.getByRole("dialog", { name: "ev-repeat-failure" })).toBeVisible();
  await page.screenshot({ path: frame("03-coding-evidence"), fullPage: false });
  await page.getByRole("button", { name: "关闭证据" }).click();
  const jsonDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出 JSON" }).click();
  const jsonFile = await jsonDownload;
  const jsonPath = await jsonFile.path();
  expect(jsonPath).not.toBeNull();
  const exported = JSON.parse(await readFile(jsonPath!, "utf-8"));
  expect(exported.metadata.mode).toBe("live");
  expect(exported.metadata.model).toBe("hy3-preview");

  await page.getByRole("button", { name: "分析研究证据漂移" }).click();
  const researchFinding = page.getByRole("heading", {
    name: "step-006-unsupported-causal-leap",
  });
  await expect(researchFinding).toBeVisible({ timeout: 90_000 });
  await expect(page.locator(".mode-badge")).toHaveText("在线 Hy3");
  const analysisElapsedMs = Date.now() - startedAt;
  expect(analysisElapsedMs).toBeLessThan(120_000);
  await researchFinding.scrollIntoViewIfNeeded();
  await page.screenshot({ path: frame("04-research-divergence"), fullPage: false });
  await page.getByRole("button", { name: "ev-source-a" }).first().click();
  await expect(page.getByRole("dialog", { name: "ev-source-a" })).toBeVisible();
  await page.screenshot({ path: frame("05-research-evidence"), fullPage: false });
  await page.getByRole("button", { name: "关闭证据" }).click();
  const markdownDownload = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出 Markdown" }).click();
  await markdownDownload;
  console.log(`live Hy3 analysis runtime: ${analysisElapsedMs} ms`);
});
