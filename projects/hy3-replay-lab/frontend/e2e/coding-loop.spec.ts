import { readFile } from "node:fs/promises";

import { expect, test } from "@playwright/test";


test("编程循环生成有证据支撑的复盘报告并导出 JSON", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "分析编程循环" }).click();

  await expect(page.getByRole("heading", { name: "step-006-repeat-patch" })).toBeVisible();
  await expect(page.getByTestId("timeline-step-step-006-repeat-patch")).toHaveAttribute(
    "data-divergence",
    "true",
  );
  await expect(page.getByText("实现连续分隔符折叠", { exact: false })).toBeVisible();

  await page.getByRole("button", { name: "ev-repeat-failure" }).first().click();
  await expect(page.getByRole("heading", { name: "ev-repeat-failure" })).toBeVisible();
  await expect(page.getByText("预期 alpha-beta", { exact: false })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出 JSON" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("轨迹复盘报告.json");
  const downloadPath = await download.path();
  expect(downloadPath).not.toBeNull();
  const exported = JSON.parse(await readFile(downloadPath!, "utf-8"));
  expect(exported.finding.first_divergence_step_id).toBe("step-006-repeat-patch");
});
