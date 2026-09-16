import { test, expect, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import type { Doc, Block } from "../src/types";

const matrix = String.raw`A=\begin{bmatrix}a&b\\c&d\end{bmatrix},\quad A^{-1}=\frac{1}{ad-bc}\begin{bmatrix}d&-b\\-c&d\end{bmatrix}`;
const formulas = [
  String.raw`\int_0^\infty e^{-x^2}\,dx=\frac{\sqrt{\pi}}{2}`,
  matrix,
  String.raw`\nabla\cdot\mathbf{E}=\frac{\rho}{\varepsilon_0}`,
];

// Stable UI fixtures; this suite tests editing/export, NOT model accuracy or crop fidelity.
// The real academic OCR sample remains covered by app.spec.ts and manual visual QA.
async function fixture(page: Page) {
  await page.request.get("/api/session");
  const upload = await page.request.post("/api/documents", {
    multipart: {
      title: "公式交互验收",
      page_range: "1",
      files: {
        name: "native-text.pdf",
        mimeType: "application/pdf",
        buffer: await fs.readFile("public/examples/native-text.pdf"),
      },
    },
  });
  expect(upload.status()).toBe(201);
  let doc: Doc = await upload.json();
  await page.request.post(`/api/documents/${doc.id}/start`, {
    data: { version: doc.version, mode: "document" },
  });
  await expect
    .poll(
      async () => {
        doc = await (await page.request.get(`/api/documents/${doc.id}`)).json();
        return doc.status;
      },
      { timeout: 45_000 },
    )
    .toBe("ready_for_review");
  doc.pages[0].blocks = formulas.map((latex, i): Block => ({
    id: `formula-fixture-${i}`,
    kind: "formula",
    bbox: [0.1, 0.1 + i * 0.2, 0.9, 0.25 + i * 0.2],
    text: latex,
    latex,
    original_text: latex,
    cells: [],
    confidence: null,
    source: "manual",
    warning: "UI fixture only",
    display: true,
    verified: true,
  }));
  const saved = await page.request.put(`/api/documents/${doc.id}`, {
    data: doc,
  });
  expect(saved.ok()).toBeTruthy();
  await page.goto("/");
  await page.getByRole("button", { name: "最近文档", exact: true }).click();
  await page.getByRole("button", { name: "打开文档", exact: true }).click();
  return doc.id;
}

test("formula reading, matrix cancel/apply, persistence and PNG", async ({
  page,
}, testInfo) => {
  const errors: string[] = [],
    external: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (
      /^https?:/.test(r.url()) &&
      !r.url().startsWith("http://127.0.0.1:8765/")
    )
      external.push(r.url());
  });
  const id = await fixture(page);
  const cards = page.locator(".formula-reading-card");
  await expect(cards).toHaveCount(3);
  await expect(cards.first().getByLabel(/块 LaTeX/)).toBeHidden();
  expect(
    await page.evaluate(() =>
      performance
        .getEntriesByType("resource")
        .some((e) => /VisualFormulaEditor.*\.js/.test(e.name)),
    ),
  ).toBe(false);
  const card = cards.nth(1);
  const source = card.getByLabel(/块 LaTeX/);
  await card.getByRole("button", { name: "修改公式", exact: true }).click();
  const field = page.locator("math-field");
  await expect(field).toBeVisible();
  for (const key of ["Control+End", "ArrowLeft", "Backspace"])
    await field.press(key);
  await field.pressSequentially("a");
  await page.getByRole("button", { name: "取消修改", exact: true }).click();
  await page.getByRole("button", { name: "放弃本次修改", exact: true }).click();
  await card.getByText("高级：公式代码与显示设置", { exact: true }).click();
  await expect(source).toHaveValue(matrix);
  await expect(
    card.getByRole("checkbox", { name: "已对照原图核对", exact: true }),
  ).toBeChecked();
  await card.getByRole("button", { name: "修改公式", exact: true }).click();
  for (const key of ["Control+End", "ArrowLeft", "Backspace"])
    await field.press(key);
  await field.pressSequentially("a");
  await page.getByRole("button", { name: "应用修改", exact: true }).click();
  await expect(source).toHaveValue(/-c\s*&\s*a\\end\{bmatrix\}$/);
  await expect(
    card.getByRole("checkbox", { name: "已对照原图核对", exact: true }),
  ).not.toBeChecked();
  await page.getByRole("button", { name: "保存", exact: true }).click();
  const saved: Doc = await (
    await page.request.get(`/api/documents/${id}`)
  ).json();
  expect(saved.pages[0].blocks[1].original_text).toBe(matrix);
  expect(saved.pages[0].blocks[1].latex).toMatch(/-c\s*&\s*a\\end\{bmatrix\}$/);
  for (let i = 0; i < 3; i++) {
    await cards
      .nth(i)
      .getByRole("button", { name: "公式图片", exact: true })
      .click();
    const png = page.getByRole("img", { name: "将要下载的公式图片" });
    await expect(png).toBeVisible();
    expect(
      await png.evaluate(
        (el: HTMLImageElement) =>
          el.naturalWidth > 100 && el.naturalHeight > 60,
      ),
    ).toBe(true);
    const download = page.waitForEvent("download");
    await page.getByRole("link", { name: "下载 PNG", exact: true }).click();
    const file = await download;
    await file.saveAs(testInfo.outputPath(`formula-${i}.png`));
    expect(await file.failure()).toBeNull();
    await page.getByRole("button", { name: "关闭公式窗口" }).click();
  }
  await card.getByRole("button", { name: "修改公式", exact: true }).click();
  await page.getByRole("button", { name: "分式", exact: true }).click();
  await expect(page.getByRole("button", { name: "应用修改" })).toBeDisabled();
  await page.getByRole("button", { name: "取消修改", exact: true }).click();
  await page.getByRole("button", { name: "放弃本次修改", exact: true }).click();
  await source.fill(String.raw`\href{https://example.com}{x}`);
  await expect(
    card.getByRole("button", { name: "公式图片", exact: true }),
  ).toBeDisabled();
  await expect(
    card.getByRole("checkbox", { name: "已对照原图核对", exact: true }),
  ).toBeDisabled();
  await expect(card.locator(".formula-unreadable")).toBeVisible();
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
});

test("mobile formula dialog, visible keyboard and Escape", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await fixture(page);
  await page
    .getByRole("button", { name: "修改公式", exact: true })
    .first()
    .click();
  await expect(page.locator("math-field")).toBeVisible();
  await page.getByRole("button", { name: "数学键盘", exact: true }).click();
  const keyboard = page.locator(".math-keyboard-host");
  expect(
    await keyboard.evaluate((el) => el.getBoundingClientRect().height),
  ).toBeGreaterThan(100);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("button", { name: "取消修改", exact: true })
    .scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath("mobile-keyboard.png") });
  await page.getByRole("button", { name: "数学键盘", exact: true }).click();
  await page.getByRole("button", { name: "关闭公式窗口" }).press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
