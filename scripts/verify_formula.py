"""Run the real local formula engine and verify native math exports."""

import json
import shutil
import sys
import time
import zipfile
from datetime import timedelta
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from shiye.config import Settings  # noqa: E402
from shiye.exports import export_document  # noqa: E402
from shiye.formula import FormulaClient, clean_latex, formula_block  # noqa: E402
from shiye.models import Block, Document, Page  # noqa: E402
from shiye.store import now  # noqa: E402


def has_semantics(latex: str) -> bool:
    compact = latex.replace(" ", "")
    return all(token in compact for token in (r"\int", r"\infty", r"\frac", r"\sqrt", r"\pi"))


def main():
    generated = ROOT / "verification" / "generated"
    screenshots = ROOT / "verification" / "screenshots"
    generated.mkdir(parents=True, exist_ok=True)
    screenshots.mkdir(parents=True, exist_ok=True)
    region_source = ROOT / "web" / "public" / "examples" / "formula-integral.png"
    page_source = ROOT / "web" / "public" / "examples" / "formula-page.png"
    settings = Settings(data_dir=ROOT / ".data", formula_timeout=300)
    client = FormulaClient(settings)
    started = time.monotonic()
    try:
        status = client.status()
        region = client.recognize(region_source, [0.0, 0.0, 1.0, 1.0])
        scan = client.scan(page_source, min_score=0.5)
    finally:
        client.stop()

    assert status["available"] and status["model_cached"]
    assert has_semantics(clean_latex(region["latex"])), region["latex"]
    assert len(scan["formulas"]) >= 3, scan

    with Image.open(page_source) as image:
        image = image.convert("RGB")
        width, height = image.size
        draw = ImageDraw.Draw(image)
        for index, item in enumerate(scan["formulas"], start=1):
            x0, y0, x1, y1 = item["bbox"]
            draw.rectangle((x0, y0, x1, y1), outline="#7c3aed", width=5)
            draw.rounded_rectangle((x0, max(0, y0 - 32), x0 + 42, y0), radius=6, fill="#7c3aed")
            draw.text((x0 + 12, max(1, y0 - 28)), str(index), fill="white")
        image.save(screenshots / "08-formula-detection.png")

    export_folder = generated / "formula-assets"
    export_folder.mkdir(exist_ok=True)
    page = Page(
        source_name="formula-page.png",
        source_page=1,
        width=width,
        height=height,
        status="ready",
        engine="PaddleOCR PP-FormulaNet",
        blocks=[
            Block(kind="title", bbox=[0.08, 0.04, 0.92, 0.09], text="识页公式导出验收", verified=True),
            Block(kind="paragraph", bbox=[0.08, 0.1, 0.92, 0.14], text="以下公式应在 Word 中保持为可编辑数学对象。"),
            Block(
                kind="formula",
                bbox=[0.08, 0.18, 0.92, 0.28],
                text=r"\int_{0}^{\infty}e^{-x^2}\,dx=\frac{\sqrt{\pi}}{2}",
                latex=r"\int_{0}^{\infty}e^{-x^2}\,dx=\frac{\sqrt{\pi}}{2}",
                source="verified-fixture",
                verified=True,
            ),
            Block(
                kind="formula",
                bbox=[0.08, 0.34, 0.92, 0.5],
                text=r"A=\begin{bmatrix}a&b\\c&d\end{bmatrix},\quad A^{-1}=\frac{1}{ad-bc}\begin{bmatrix}d&-b\\-c&a\end{bmatrix}",
                latex=r"A=\begin{bmatrix}a&b\\c&d\end{bmatrix},\quad A^{-1}=\frac{1}{ad-bc}\begin{bmatrix}d&-b\\-c&a\end{bmatrix}",
                source="verified-fixture",
                verified=True,
            ),
        ],
    )
    shutil.copy2(page_source, export_folder / f"{page.id}.png")
    stamp = now()
    document = Document(
        title="识页公式导出验收",
        mode="academic",
        status="ready_for_review",
        created_at=stamp.isoformat(),
        updated_at=stamp.isoformat(),
        expires_at=(stamp + timedelta(hours=24)).isoformat(),
        pages=[page],
    )
    docx, docx_warnings = export_document(document, export_folder, generated / "formula-word", "docx")
    markdown, markdown_warnings = export_document(document, export_folder, generated / "formula-markdown", "md")
    with zipfile.ZipFile(docx) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    nodes = {name: xml.count(f"<m:{name}") for name in ("oMath", "f", "rad", "sSubSup", "m")}
    assert nodes["oMath"] >= 2 and nodes["f"] >= 2 and nodes["rad"] >= 1 and nodes["m"] >= 1
    assert '<m:degHide m:val="1"/>' in xml
    assert not any("暂不支持的 LaTeX" in item for item in docx_warnings)
    markdown_text = markdown.read_text(encoding="utf-8")
    assert r"\int_{0}^{\infty}" in markdown_text and r"\begin{bmatrix}" in markdown_text

    target_docx = generated / "formula-native.docx"
    shutil.copy2(docx, target_docx)
    shutil.copy2(markdown, generated / "formula-notes.md")
    report = {
        "verified_at": now().isoformat(),
        "runtime": {
            "engine": "PaddleOCR PP-FormulaNet",
            "model": status["model"],
            "device": status["device"],
            "paddleocr_version": status.get("paddleocr_version"),
            "paddlepaddle_version": status.get("paddlepaddle_version"),
            "model_cached": status["model_cached"],
        },
        "region_recognition": {
            "latex": clean_latex(region["latex"]),
            "semantic_tokens_present": True,
            "elapsed_ms": region.get("elapsed_ms"),
        },
        "full_page_scan": {
            "detected": len(scan["formulas"]),
            "elapsed_ms": scan.get("elapsed_ms"),
            "items": scan["formulas"],
            "note": "Synthetic page; count is a regression check, not a general accuracy score.",
        },
        "exports": {
            "docx_native_omml_nodes": nodes,
            "docx_formula_fallbacks": 0,
            "markdown_math_delimiters": markdown_text.count("$$") // 2,
            "warnings": docx_warnings + markdown_warnings,
        },
        "wall_elapsed_ms": round((time.monotonic() - started) * 1000),
    }
    (ROOT / "verification" / "formula-check.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
