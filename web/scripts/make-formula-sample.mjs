import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "@playwright/test";
import katex from "katex";

const root = path.resolve(import.meta.dirname, "..");
const output = path.join(root, "public", "examples");
await fs.mkdir(output, { recursive: true });
const css = await fs.readFile(path.join(root, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const formulas = [
  String.raw`\int_{0}^{\infty} e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}`,
  String.raw`\nabla \cdot \mathbf{E}=\frac{\rho}{\varepsilon_0}`,
  String.raw`A=\begin{bmatrix}a&b\\c&d\end{bmatrix},\quad A^{-1}=\frac{1}{ad-bc}\begin{bmatrix}d&-b\\-c&a\end{bmatrix}`,
];
const render = (value) => katex.renderToString(value, { displayMode: true, throwOnError: true, output: "htmlAndMathml" });
const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1100, height: 1500 }, deviceScaleFactor: 1 });
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8"><style>${css}
    *{box-sizing:border-box} body{margin:0;background:white;color:#171717;font-family:"Times New Roman","Microsoft YaHei",serif}
    main{width:980px;margin:0 auto;padding:70px 82px 88px} h1{font-size:34px;text-align:center;margin:0 0 22px}
    .meta{text-align:center;font-size:17px;margin-bottom:45px;color:#555} p{font-size:22px;line-height:1.9;text-align:justify;margin:22px 0}
    .equation{font-size:26px;margin:30px auto;padding:18px 12px;text-align:center} #formula3{font-size:19px}
    .note{border-left:4px solid #333;padding-left:18px}.page-number{text-align:center;margin-top:48px;font-size:16px}
  </style></head><body><main>
    <h1>数学分析与电磁学公式样例</h1><div class="meta">识页 · 学术公式模式真实验收页</div>
    <p>例 1　高斯积分是概率论与统计物理中的经典结果。下面的定积分同时包含上下限、指数、分式与根式：</p>
    <div class="equation" id="formula1">${render(formulas[0])}</div>
    <p>例 2　麦克斯韦方程组中的高斯定律给出电场散度与电荷密度之间的关系：</p>
    <div class="equation" id="formula2">${render(formulas[1])}</div>
    <p class="note">矩阵是论文和课本里常见的二维公式结构，识别后应保留行列关系，并允许在 LaTeX 或 Word 中继续编辑。</p>
    <div class="equation" id="formula3">${render(formulas[2])}</div>
    <p>使用时请对照左侧原图检查希腊字母、正负号、上下标、积分边界和括号。模型识别完成不等于内容已经人工确认。</p>
    <div class="page-number">— 1 —</div>
  </main></body></html>`, { waitUntil: "load" });
  await page.screenshot({ path: path.join(output, "formula-page.png"), fullPage: true });
  await page.locator("#formula1").screenshot({ path: path.join(output, "formula-integral.png") });
  await fs.writeFile(path.join(output, "formula-ground-truth.json"), JSON.stringify({ formulas }, null, 2) + "\n");
} finally {
  await browser.close();
}
