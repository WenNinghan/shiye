"""Generate synthetic, non-private demo inputs. No downloaded or personal data."""
import argparse
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont


def find_font():
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    raise RuntimeError("未找到中文字体。Linux 请安装 fonts-noto-cjk，或修改 make_samples.py 的字体路径。")


def generate(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    font = find_font()
    img = Image.new("RGB", (1240, 1754), "#fffefb")
    draw = ImageDraw.Draw(img)
    title = ImageFont.truetype(font, 58)
    body = ImageFont.truetype(font, 32)
    small = ImageFont.truetype(font, 25)
    draw.rounded_rectangle((88, 88, 1152, 162), radius=8, fill="#edf3e9")
    draw.text((112, 104), "AIAADC / 校园创意实验室", font=small, fill="#4a7153")
    draw.text((90, 220), "把你的想法，做成小作品", font=title, fill="#243f31")
    draw.text((92, 319), "校园项目交流日 · 活动通知", font=body, fill="#617c64")
    draw.line((92, 390, 1145, 390), fill="#bed1b6", width=2)
    lines = [
        "欢迎同学们带着自己的小项目来交流！",
        "2026年9月12日下午2点，参加项目分享活动。",
        "活动地点：创新楼 301 教室。",
        "请于2026年9月11日18:00前提交项目介绍。",
        "项目不必完美，只要有趣、有用、有自己的想法。",
        "请准备：项目名称、使用说明、一张展示截图。",
    ]
    for i, line in enumerate(lines):
        draw.text((95, 440+i*73), line, font=body, fill="#2e4938")
    draw.text((95, 946), "交流日安排", font=ImageFont.truetype(font, 40), fill="#2e4938")
    xs = [96, 320, 758, 1142]
    ys = [1035, 1120, 1205, 1290]
    draw.rectangle((xs[0], ys[0], xs[-1], ys[1]), fill="#f0f5ec")
    for x in xs:
        draw.line((x, ys[0], x, ys[-1]), fill="#667c5b", width=2)
    for y in ys:
        draw.line((xs[0], y, xs[-1], y), fill="#667c5b", width=2)
    rows = [["时间", "内容", "地点"], ["14:00", "项目展示", "301 教室"], ["15:30", "自由交流", "公共空间"]]
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            draw.text((xs[j]+20, ys[i]+24), value, font=body, fill="#3b5542")
    draw.rounded_rectangle((95, 1380, 1145, 1535), radius=9, fill="#f3f5ed")
    draw.text((122, 1407), "这是一份生成的演示通知，不含真实个人信息。", font=small, fill="#8b997f")
    draw.text((122, 1457), "识页：先校对，再导出，让每一页更好用。", font=small, fill="#8b997f")
    draw.text((95, 1620), "DEMO DOCUMENT  /  01", font=small, fill="#a1ae99")
    image_path = output / "notice.png"
    img.save(image_path)
    pdf = fitz.open()
    p = pdf.new_page(width=595, height=842)
    p.insert_image(p.rect, filename=str(image_path))
    pdf.save(output/"scanned-notice.pdf")
    pdf.close()
    native = fitz.open()
    for i in range(2):
        p = native.new_page()
        p.insert_text((50, 70), f"原生文字测试 第{i+1}页", fontname="china-s", fontsize=22)
        p.insert_text((50, 120), "识页支持中文和 English 123，文字无需再次 OCR。", fontname="china-s", fontsize=13)
        p.insert_text((50, 150), "2026年9月12日下午2点参加项目分享活动。", fontname="china-s", fontsize=13)
    native.save(output/"native-text.pdf")
    native.close()
    print(f"Created synthetic PNG, scanned PDF and native PDF in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1]/"web/public/examples")
    generate(parser.parse_args().output)
