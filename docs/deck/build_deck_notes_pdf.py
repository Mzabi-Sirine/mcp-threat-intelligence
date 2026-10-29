#!/usr/bin/env python3
"""Assemble un PDF imprimable : chaque diapo avec son mémo oral en dessous."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from deck_content import MEMOS, SLIDES  # noqa: E402

DECK = HERE / "Deck_Soutenance_MCP_TI.pdf"
OUT = HERE / "Deck_Soutenance_MCP_TI_notes.pdf"
DPI = 150
PAGE = (1240, 1754)  # A4 portrait à 150 dpi
MARGIN = 60
NAVY = (11, 31, 58)
BLUE = (31, 95, 168)
INK = (28, 37, 48)
MUTED = (96, 108, 124)
PANEL = (244, 247, 251)
WHITE = (255, 255, 255)
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(FONT_DIR / name), size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=fnt) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_slides(tmp: Path) -> list[Image.Image]:
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(DPI), str(DECK), str(tmp / "slide")],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    images = []
    for path in sorted(tmp.glob("slide-*.png")):
        image = Image.open(path).convert("RGB")
        images.append(image.resize((1120, 630), Image.LANCZOS))
    return images


def build_page(slide_img: Image.Image, s: dict, n: int, total: int) -> Image.Image:
    page = Image.new("RGB", PAGE, WHITE)
    draw = ImageDraw.Draw(page)

    draw.rectangle([0, 0, PAGE[0], 46], fill=NAVY)
    draw.text((MARGIN, 14), f"Diapo {n}/{total} · {s['section']}", font=font(15, True), fill=WHITE)
    right = "TEK-UP SSIR · MCP Threat Intelligence"
    draw.text((PAGE[0] - MARGIN - draw.textlength(right, font=font(15)), 14), right,
              font=font(15), fill=WHITE)

    page.paste(slide_img, (MARGIN, 92))

    body = font(26)
    bullets = MEMOS.get(n, [])
    line_height = 37
    wrapped = [wrap(draw, bullet, body, 1000) for bullet in bullets]
    content_h = 52 + 44 + sum(len(lines) * line_height + 12 for lines in wrapped)
    panel_top = 752
    panel_bottom = min(1670, panel_top + 26 + content_h + 22)
    draw.rounded_rectangle([MARGIN, panel_top, PAGE[0] - MARGIN, panel_bottom], radius=14,
                           fill=PANEL)
    draw.rectangle([MARGIN, panel_top + 18, MARGIN + 7, panel_bottom - 18], fill=BLUE)

    x = MARGIN + 34
    y = panel_top + 26
    draw.text((x, y), "À DIRE (simple)", font=font(30, True), fill=NAVY)
    y += 52
    draw.text((x, y), f"durée conseillée : {s['duration']}", font=font(19), fill=MUTED)
    y += 44

    for lines in wrapped:
        draw.text((x, y), "•", font=body, fill=BLUE)
        for i, line in enumerate(lines):
            draw.text((x + 28, y + i * line_height), line, font=body, fill=INK)
        y += len(lines) * line_height + 12

    footer = f"Notes de soutenance — Mzabi Sirine · Khaled Ellif · diapo {n}/{total}"
    draw.text((MARGIN, 1706), footer, font=font(16), fill=MUTED)
    num = f"{n} / {total}"
    draw.text((PAGE[0] - MARGIN - draw.textlength(num, font=font(16)), 1706), num,
              font=font(16), fill=MUTED)
    return page


def main() -> int:
    if not DECK.exists():
        print("deck PDF absent :", DECK)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        slides = render_slides(Path(tmp))
    if len(slides) != len(SLIDES):
        print(f"incohérence : {len(slides)} images pour {len(SLIDES)} diapos")
        return 1
    pages = [build_page(img, s, s["n"], len(SLIDES)) for img, s in zip(slides, SLIDES)]
    pages[0].save(OUT, "PDF", resolution=float(DPI), save_all=True, append_images=pages[1:])
    print(f"NOTES PDF: {OUT}")
    print(f"PAGES: {len(pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
