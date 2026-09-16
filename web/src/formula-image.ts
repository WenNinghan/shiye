import { toBlob } from "html-to-image";

/** Capture the full typeset formula, never the scrolled/clipped card or its controls. */
export async function formulaPng(source: HTMLElement): Promise<Blob> {
  await document.fonts.ready;
  const stage = document.createElement("div");
  stage.style.cssText =
    "position:fixed;left:-100000px;top:0;pointer-events:none;";
  stage.setAttribute("aria-hidden", "true");
  const canvas = document.createElement("div");
  canvas.style.cssText =
    "display:inline-block;width:max-content;max-width:none;padding:24px;background:#fff;color:#182b24;";
  const clone = source.cloneNode(true) as HTMLElement;
  clone.style.cssText = `font-size:${getComputedStyle(source).fontSize};width:max-content;max-width:none;overflow:visible;`;
  clone.querySelectorAll(".katex-mathml").forEach((node) => node.remove());
  canvas.appendChild(clone);
  stage.appendChild(canvas);
  document.body.appendChild(stage);
  try {
    await document.fonts.ready;
    const width = Math.ceil(canvas.getBoundingClientRect().width);
    const height = Math.ceil(canvas.getBoundingClientRect().height);
    if (
      !width ||
      !height ||
      width > 8000 ||
      height > 8000 ||
      width * height > 4_000_000
    ) {
      throw Error("公式过长，无法生成清晰图片。请分段处理或导出 Word。");
    }
    const blob = await toBlob(canvas, {
      width,
      height,
      pixelRatio: 2,
      backgroundColor: "#ffffff",
      preferredFontFormat: "woff2",
    });
    if (!blob) throw Error("公式图片生成失败，请重试或导出 Word。");
    return blob;
  } finally {
    stage.remove();
  }
}
