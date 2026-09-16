import { test, expect } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const screenshots = path.resolve("../verification/screenshots");
const generated = path.resolve("../verification/generated");

test.beforeAll(async ({request}) => {
  await expect.poll(async () => {
    try { return (await request.get('/api/health', {timeout:2000})).status(); }
    catch { return 0; }
  }, {timeout:60_000, message:'先启动识页本机服务，再执行浏览器验收'}).toBe(200);
  await fs.mkdir(screenshots, { recursive: true });
  await fs.mkdir(generated, { recursive: true });
});

test("desktop: real OCR, correction, table, all exports and confirmed calendar", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "选择文件", exact: true }),
  ).toBeEnabled();
  await page.screenshot({
    path: path.join(screenshots, "01-home-desktop.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: /用示例体验一下/ }).click();
  await expect(
    page.getByRole("button", { name: "开始识别", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "开始识别", exact: true }).click();
  await expect(
    page.getByText("识别完成，请校对后导出", { exact: false }),
  ).toBeVisible({ timeout: 150_000 });
  await expect(page.locator(".block-card")).not.toHaveCount(0);
  const text = page.getByRole("textbox", { name: "第 1 块内容", exact: true });
  await text.fill("识页：已人工校对的中文标题");
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await expect(
    page.getByText("校对内容已保存。", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "表格第 2 行第 2 列", exact: true }),
  ).toHaveValue("项目展示");
  await page.screenshot({
    path: path.join(screenshots, "02-workspace-desktop.png"),
    fullPage: true,
  });
  for (const [format, name] of [
    ["docx", "corrected.docx"],
    ["pdf-searchable", "searchable.pdf"],
    ["pdf-image", "images.pdf"],
    ["md", "notes.md"],
    ["txt", "notes.txt"],
    ["json", "document.json"],
  ]) {
    await page.getByLabel("导出格式", { exact: true }).selectOption(format);
    await page
      .getByRole("button", { name: "生成导出文件", exact: true })
      .click();
    const link = page.getByRole("link", { name: "下载文件", exact: true });
    await expect(link).toBeVisible();
    const downloadPromise = page.waitForEvent("download");
    await link.click();
    const download = await downloadPromise;
    await download.saveAs(path.join(generated, name));
    expect(await download.failure()).toBeNull();
  }
  await page.getByRole("button", { name: "通知转待办", exact: true }).click();
  await page
    .getByRole("button", { name: "从整份文档提取候选事项", exact: true })
    .click();
  await expect(page.locator(".task-card")).not.toHaveCount(0);
  const dateInputs = page.locator('.task-card input[type="date"]');
  const count = await dateInputs.count();
  let confirmed = false;
  for (let index = 0; index < count; index++) {
    if (await dateInputs.nth(index).inputValue()) {
      await page.locator(".task-card").nth(index).getByRole("checkbox").check();
      confirmed = true;
      break;
    }
  }
  expect(confirmed).toBeTruthy();
  const calendar = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "导出已确认事项 .ics", exact: true })
    .click();
  await (await calendar).saveAs(path.join(generated, "tasks.ics"));
  await page.screenshot({
    path: path.join(screenshots, "03-tasks-desktop.png"),
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("native PDF selection, page reordering, transform and deletion", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "选择文件", exact: true }),
  ).toBeEnabled();
  await page
    .locator("input[type=file]")
    .setInputFiles("public/examples/native-text.pdf");
  await page.getByLabel("PDF 页码", { exact: true }).fill("1-2");
  await page.getByRole("button", { name: "导入并整理", exact: true }).click();
  await expect(page.locator(".page-thumb")).toHaveCount(2);
  await page.getByRole("button", { name: "开始识别", exact: true }).click();
  await expect(
    page.getByText("识别完成，请校对后导出", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "页面下移", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await expect(
    page.getByText("校对内容已保存。", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "选择第 1 页", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "第 1 块内容", exact: true }),
  ).toHaveValue("原生文字测试 第2页");
  page.on("dialog", (dialog) => dialog.accept());
  await page
    .getByRole("button", { name: "顺时针旋转 90 度", exact: true })
    .click();
  await expect(
    page.getByText("图像已更新，本页需要重新识别；旧导出已清理", {
      exact: false,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: /最近文档/ }).click();
  await page.getByRole("button", { name: "彻底删除文档", exact: true }).click();
  await expect(page.getByText("这里还没有文档", { exact: true })).toBeVisible();
});

test("mobile home, upload, OCR workspace and no horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "选择文件", exact: true }),
  ).toBeEnabled();
  await page.screenshot({
    path: path.join(screenshots, "04-home-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page
    .locator("input[type=file]")
    .setInputFiles("public/examples/native-text.pdf");
  await page.getByRole("button", { name: "导入并整理", exact: true }).click();
  await page.getByRole("button", { name: "开始识别", exact: true }).click();
  await expect(
    page.getByText("识别完成，请校对后导出", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: path.join(screenshots, "05-workspace-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("academic mode: automatic formula scan, KaTeX review and Word export", async ({
  page,
}) => {
  const statusResponse = await page.request.get("/api/formula/status");
  const formulaStatus = await statusResponse.json();
  test.skip(
    !formulaStatus.available,
    "Optional formula runtime is not installed on this machine",
  );

  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByText("PP-FormulaNet · 就绪", { exact: true })).toBeVisible();
  await page
    .locator("input[type=file]")
    .setInputFiles("public/examples/formula-page.png");
  await page.getByRole("radio", { name: /学术公式/ }).click();
  await page.getByRole("button", { name: "导入并整理", exact: true }).click();
  await expect(page.getByText("学术公式", { exact: true }).last()).toBeVisible();
  await page.getByRole("button", { name: "开始识别", exact: true }).click();
  const formulas = page.locator(".formula-editor");
  await expect(formulas).toHaveCount(3, { timeout: 180_000 });
  await expect(page.getByText(/学术识别完成，共找到 3 个公式/)).toBeVisible();
  const firstLatex = formulas.first().getByLabel(/块 LaTeX/);
  await expect(firstLatex).toBeHidden();
  await formulas.first().getByText("高级：公式代码与显示设置", { exact: true }).click();
  await expect(firstLatex).toHaveValue(/\\int/);
  await expect(firstLatex).toHaveValue(/\\frac/);
  await formulas.first().getByText("高级：公式代码与显示设置", { exact: true }).click();
  await expect(formulas.first().locator(".katex")).toBeVisible();
  await formulas
    .first()
    .getByRole("checkbox", { name: "已对照原图核对", exact: true })
    .check();
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await expect(page.getByText("校对内容已保存。", { exact: true })).toBeVisible();
  await page.screenshot({
    path: path.join(screenshots, "10-formula-workspace.png"),
    fullPage: true,
  });

  await page.getByLabel("导出格式", { exact: true }).selectOption("docx");
  await page.getByRole("button", { name: "生成导出文件", exact: true }).click();
  const link = page.getByRole("link", { name: "下载文件", exact: true });
  await expect(link).toBeVisible();
  const downloadPromise = page.waitForEvent("download");
  await link.click();
  const download = await downloadPromise;
  await download.saveAs(path.join(generated, "formula-ui.docx"));
  expect(await download.failure()).toBeNull();
  expect(errors).toEqual([]);
});
