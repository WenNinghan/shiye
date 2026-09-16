"""Bounded input decoding and CPU OCR. No network calls or document macros."""
import io
import math
import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageOps

from .models import Block, Page, uid

Image.MAX_IMAGE_PIXELS = 32_000_000


def normalized(rect, width, height):
    return [max(0.0, min(1.0, v / size)) for v, size in zip(rect, [width, height, width, height])]


def parse_page_range(value: str, total: int) -> list[int]:
    if not value.strip():
        return list(range(total))
    selected = set()
    for part in value.replace("，", ",").split(","):
        match = re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*", part)
        if not match:
            raise ValueError("页码格式应为 1-3,5")
        start = int(match[1])
        end = int(match[2] or start)
        if start < 1 or end < start or end > total:
            raise ValueError(f"页码超出范围：本文件共 {total} 页")
        if end - start > 1000:
            raise ValueError("选取页数过多")
        selected.update(range(start - 1, end))
    return sorted(selected)


def ingest(data: bytes, filename: str, folder: Path, settings, page_range="") -> list[Page]:
    folder.mkdir(parents=True, exist_ok=True)
    if data.startswith(b"%PDF-"):
        with fitz.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise ValueError("此 PDF 已加密，请先在本机解密后上传")
            indices = parse_page_range(page_range, len(pdf))
            if len(indices) > settings.max_pages:
                raise ValueError(f"一次最多处理 {settings.max_pages} 页，请填写 PDF 页码范围")
            result = []
            for index in indices:
                original = pdf[index]
                # Rasterize at 150 dpi, then cap decoded dimensions before allocating pixels.
                scale = min(150 / 72, math.sqrt(settings.max_pixels / max(1, original.rect.width * original.rect.height)))
                pix = original.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)
                page = Page(source_name=filename, source_page=index + 1, width=pix.width, height=pix.height)
                pix.save(folder / f"{page.id}.png")
                native = original.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)
                image_rects = [x["bbox"] for x in original.get_image_info()]
                image_area = sum(max(0, (r[2]-r[0])*(r[3]-r[1])) for r in image_rects)
                # A rotated or scanned/mixed page is OCR'd as displayed, avoiding coordinate drift.
                use_native = original.rotation == 0 and image_area < original.rect.get_area() * 0.45
                if use_native:
                    for item in native["blocks"]:
                        if item.get("type") != 0:
                            continue
                        spans = [s for line in item["lines"] for s in line["spans"]]
                        text = "\n".join("".join(s["text"] for s in line["spans"]) for line in item["lines"]).strip()
                        if text:
                            kind = "title" if len(text) < 90 and max((s["size"] for s in spans), default=0) >= 16 else "paragraph"
                            page.blocks.append(Block(kind=kind, bbox=normalized(item["bbox"], original.rect.width, original.rect.height), text=text, original_text=text, source="native-pdf", confidence=1))
                    if sum(len(b.text) for b in page.blocks) >= 12:
                        page.engine = "PDF 原生文字"
                        # Use actual PDF ruling lines, not a guessed column layout.
                        try:
                            for table in original.find_tables().tables:
                                cells = [[value or "" for value in row] for row in table.extract()]
                                if not cells or len(cells) > 100 or max(map(len, cells)) > 50:
                                    continue
                                bbox = normalized(table.bbox, original.rect.width, original.rect.height)
                                page.blocks = [b for b in page.blocks if not (bbox[0] <= (b.bbox[0]+b.bbox[2])/2 <= bbox[2] and bbox[1] <= (b.bbox[1]+b.bbox[3])/2 <= bbox[3])]
                                text = "\n".join("\t".join(row) for row in cells)
                                page.blocks.append(Block(kind="table", cells=cells, text=text, original_text=text, bbox=bbox, source="native-pdf-table", warning="PDF 表格请逐格核对；合并单元格按普通矩形表格导出。"))
                        except (ValueError, RuntimeError):
                            pass  # Native paragraphs remain available if table analysis fails.
                        for rect in image_rects:
                            page.blocks.append(Block(kind="image", bbox=normalized(rect, original.rect.width, original.rect.height), source="native-pdf"))
                        page.blocks.sort(key=lambda b: (round(b.bbox[1], 2), b.bbox[0]))
                    else:
                        page.blocks = []
                result.append(page)
            return result
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("仅支持 PNG、JPG、WebP 和 PDF；请先转换其他格式")
            if source.width * source.height > settings.max_pixels:
                raise ValueError("图片像素过大，请缩小至 3200 万像素以内")
            img = ImageOps.exif_transpose(source).convert("RGBA")
            white = Image.new("RGBA", img.size, "white")
            white.alpha_composite(img)
            img = white.convert("RGB")
            page = Page(source_name=filename, source_page=1, width=img.width, height=img.height)
            img.save(folder / f"{page.id}.png")
            return [page]
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("图片解码尺寸超出安全限制") from exc
    except (OSError, SyntaxError) as exc:
        raise ValueError("文件不是有效的图片或 PDF，或文件已经损坏") from exc


def _grid_tables(rgb, rows, width, height):
    """Conservative ruled-table detection. No claim of borderless/merged-cell recovery."""
    import cv2
    import numpy as np
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    binary = cv2.threshold(gray, 190, 255, cv2.THRESH_BINARY_INV)[1]
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (max(35, width // 18), 1)))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(30, height // 25))))
    mask = cv2.bitwise_or(horizontal, vertical)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    tables, consumed = [], set()

    def clusters(values):
        groups = []
        for v in values:
            if not groups or v - groups[-1][-1] > 4:
                groups.append([int(v)])
            else:
                groups[-1].append(int(v))
        return [round(sum(g) / len(g)) for g in groups]

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < width * 0.2 or h < 70:
            continue
        xs = clusters(np.where((vertical[y:y+h, x:x+w] > 0).sum(axis=0) > h * 0.75)[0])
        ys = clusters(np.where((horizontal[y:y+h, x:x+w] > 0).sum(axis=1) > w * 0.75)[0])
        if not (3 <= len(xs) <= 21 and 3 <= len(ys) <= 51):
            continue
        cells = [["" for _ in xs[:-1]] for _ in ys[:-1]]
        found = []
        for idx, row in enumerate(rows):
            box, text, score = row[:3]
            cx = sum(p[0] for p in box) / 4 - x
            cy = sum(p[1] for p in box) / 4 - y
            col = next((i for i in range(len(xs)-1) if xs[i] <= cx <= xs[i+1]), None)
            line = next((i for i in range(len(ys)-1) if ys[i] <= cy <= ys[i+1]), None)
            if col is not None and line is not None:
                cells[line][col] += (" " if cells[line][col] else "") + text
                found.append(idx)
        if len(found) < 2:
            continue
        text = "\n".join("\t".join(r) for r in cells)
        tables.append(Block(kind="table", bbox=normalized([x, y, x+w, y+h], width, height), cells=cells, text=text, original_text=text, source="ruled-table", warning="简单有线表格识别，请核对单元格；不支持自动还原合并单元格。"))
        consumed.update(found)
    return tables, consumed


def _prefer_latin_spacing(original: str, candidate: str, confidence: float) -> str:
    """Accept a second OCR result only when it changes whitespace and nothing else."""
    candidate = re.sub(r"\s+", " ", candidate.strip())
    if confidence < 0.85 or not re.search(r"[A-Za-z]", original):
        return original
    if sum(ch.isspace() for ch in candidate) <= sum(ch.isspace() for ch in original):
        return original
    if "".join(original.split()) != "".join(candidate.split()):
        return original
    return candidate


def _restore_latin_spacing(engine, bgr, rows):
    """Re-read wider line crops to recover word gaps lost by tight detection boxes."""
    updated = [list(row) for row in rows]
    crops = []
    crop_rows = []
    image_height, image_width = bgr.shape[:2]

    for index, row in enumerate(rows):
        box, text = row[:2]
        if not re.search(r"[A-Za-z]", str(text)):
            continue
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]
        line_height = max(1.0, max(ys) - min(ys))
        for padding_factor in (0.0, 0.15, 0.30, 0.50):
            vertical_padding = line_height * padding_factor
            x0 = max(0, math.floor(min(xs)))
            y0 = max(0, math.floor(min(ys) - vertical_padding))
            x1 = min(image_width, math.ceil(max(xs)) + 1)
            y1 = min(image_height, math.ceil(max(ys) + vertical_padding) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            crops.append(bgr[y0:y1, x0:x1])
            crop_rows.append(index)

    if not crops:
        return updated

    try:
        # rapidocr-onnxruntime 1.4.x exposes its batched recognizer on the
        # initialized engine. If that adapter ever changes, normal OCR remains
        # available and this optional whitespace repair simply becomes a no-op.
        candidates, _ = engine.text_rec(crops, False)
    except Exception:
        return updated

    best = {}
    for index, result in zip(crop_rows, candidates or []):
        if not result or len(result) < 2:
            continue
        candidate, confidence = str(result[0]), float(result[1])
        original = str(rows[index][1])
        candidate = _prefer_latin_spacing(original, candidate, confidence)
        if candidate == original:
            continue
        rank = (sum(ch.isspace() for ch in candidate), confidence)
        if index not in best or rank > best[index][0]:
            best[index] = (rank, candidate)

    for index, (_, candidate) in best.items():
        updated[index][1] = candidate
    return updated


def recognize_image(path: str) -> tuple[list[dict], str]:
    import cv2
    import numpy as np
    from rapidocr_onnxruntime import RapidOCR
    cv2.setNumThreads(2)
    engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
    with Image.open(path) as im:
        rgb = np.array(im.convert("RGB"))
        width, height = im.size
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    rows, _ = engine(bgr)
    rows = rows or []
    rows = _restore_latin_spacing(engine, bgr, rows)
    tables, consumed = _grid_tables(rgb, rows, width, height)
    text_heights = sorted(max(p[1] for p in row[0])-min(p[1] for p in row[0]) for row in rows)
    median = text_heights[len(text_heights)//2] if text_heights else 20
    blocks = tables
    for idx, row in enumerate(rows):
        if idx in consumed:
            continue
        box, text, confidence = row[:3]
        rect = [min(p[0] for p in box), min(p[1] for p in box), max(p[0] for p in box), max(p[1] for p in box)]
        kind = "title" if rect[3]-rect[1] > median * 1.35 and len(text) < 60 else "list" if re.match(r"^([•●·]|\d+[.、])", text) else "paragraph"
        blocks.append(Block(kind=kind, bbox=normalized(rect, width, height), text=text, original_text=text, confidence=float(confidence), source="rapidocr", warning="识别把握较低，请对照原图" if confidence < 0.85 else ""))
    blocks.sort(key=lambda b: (round(b.bbox[1], 2), b.bbox[0]))
    if not blocks:
        blocks = [Block(kind="image", bbox=[0, 0, 1, 1], source="fallback", warning="未检出文字，保留原图。可手动添加文字，或裁剪、旋转后重试。")]
    return [b.model_dump() for b in blocks], "RapidOCR · 中文 CPU"


def recognize_child(path, connection):
    try:
        connection.send({"ok": True, "result": recognize_image(path)})
    except Exception as exc:
        connection.send({"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:300]}"})
    finally:
        connection.close()
