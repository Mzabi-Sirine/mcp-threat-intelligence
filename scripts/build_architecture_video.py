#!/usr/bin/env python3
"""Vidéo pédagogique de l'architecture du projet (1920x1080, voix off FR)."""

from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[1]
BASE = PROJECT / "figures" / "fig_architecture_zones.png"
LOGO = PROJECT / "figures" / "logoTek-up_university.png"
OUT = PROJECT / "preuves" / "video" / "Demo_Architecture_MCP_TI.mp4"
WORK = PROJECT / "preuves" / "video" / "architecture"

W, H = 1920, 1080
NAVY = (16, 36, 63)
GOLD = (138, 109, 31)
GOLD_BRIGHT = (201, 162, 39)
INK = (31, 42, 58)
GREY = (90, 102, 118)
LIGHT = (243, 246, 250)
PALE_BLUE = (231, 239, 248)
PALE_GREEN = (237, 246, 241)
PALE_GOLD = (251, 246, 227)
PALE_RED = (251, 240, 240)
WHITE = (255, 255, 255)
BLUE = (43, 92, 138)
GREEN = (46, 125, 91)
RED = (166, 59, 59)

FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

ZONES = {
    "Z0": {"box": (0.030, 0.155, 0.290, 0.795), "color": BLUE, "fill": PALE_BLUE,
           "badge": "ZONE 0", "title": "Poste analyste",
           "bullets": [
               "Agent LLM / client MCP en stdio, JSON-RPC 2.0",
               "Jeton de capacité signé, porté par le client",
               "Attestation de posture : EDR, chiffrement, OS ≤ 24 h",
               "Aucun accès direct aux données",
           ],
           "cp": "CP1 · Authentification"},
    "Z1": {"box": (0.310, 0.155, 0.720, 0.795), "color": GREEN, "fill": PALE_GREEN,
           "badge": "ZONE 1", "title": "Processus MCP",
           "bullets": [
               "Une seule porte d'entrée, un seul journal",
               "Authentification HMAC, puis décision ABAC",
               "Six outils en lecture seule, schémas stricts",
               "Assainissement, étiquetage, limiteur, audit",
           ],
           "cp": "CP1 → CP7"},
    "Z2": {"box": (0.740, 0.155, 0.970, 0.795), "color": GOLD, "fill": PALE_GOLD,
           "badge": "ZONE 2", "title": "Données classifiées",
           "bullets": [
               "SQLite ouvert en lecture seule (0440 au repos)",
               "Bulletins étiquetés : 0 Public → 3 Secret",
               "Clé HMAC 0400, hors base, lue au démarrage",
               "Journal append-only, chaîné",
           ],
           "cp": "CP8 · Lecture filtrée"},
    "Z3": {"box": (0.035, 0.025, 0.965, 0.140), "color": RED, "fill": PALE_RED,
           "badge": "ZONE 3", "title": "Flux partenaires",
           "bullets": [
               "Contenu importé, potentiellement hostile",
               "Ingestion hors ligne : validation",
               "Neutralisation avant stockage",
               "Étiquetage à l'entrée",
           ],
           "cp": "CP3 · CP4"},
}

SLIDES = [
    {"kind": "title", "min": 9.0,
     "voice": "Voici l'architecture du projet : quatre zones de confiance et huit points de contrôle."},
    {"kind": "overview", "min": 12.0,
     "voice": "Le client ne parle jamais directement aux données. Toute requête traverse le processus MCP, "
              "qui applique les contrôles avant de lire la base."},
    {"kind": "zone", "zone": "Z0", "min": 12.0,
     "voice": "Zone zéro : le poste analyste. L'agent porte un jeton signé et une attestation de posture ; "
              "il n'a aucun accès direct aux données."},
    {"kind": "zone", "zone": "Z1", "min": 14.0,
     "voice": "Zone un : le processus MCP, au moindre privilège. Authentification, décision ABAC, six outils "
              "en lecture seule, assainissement, étiquetage, limiteur et journal."},
    {"kind": "zone", "zone": "Z2", "min": 13.0,
     "voice": "Zone deux : les données classifiées. La base SQLite est ouverte en lecture seule, "
              "la clé HMAC reste hors base et le journal est chaîné."},
    {"kind": "zone", "zone": "Z3", "min": 12.0,
     "voice": "Zone trois : les flux partenaires, non fiables. L'ingestion est hors ligne : validation, "
              "neutralisation, puis étiquetage avant stockage."},
    {"kind": "flow", "min": 15.0,
     "voice": "Le parcours est linéaire : jeton, authentification, ABAC, outil, assainissement, enveloppe "
              "étiquetée, journal, puis réponse filtrée. Huit points de contrôle."},
    {"kind": "outro", "min": 10.0,
     "voice": "Quatre zones, huit points de contrôle, un seul journal. L'architecture est décrite et testée "
              "dans le rapport."},
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_paragraph(draw, xy, text, fnt, fill, max_width, line_gap=8):
    x, y = xy
    for line in wrap(draw, text, fnt, max_width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + line_gap
    return y


def base_canvas() -> Image.Image:
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    draw.text((60, 42), "ARCHITECTURE · SERVEUR MCP DE THREAT INTELLIGENCE", font=font(20, True), fill=NAVY)
    draw.text((W - 330, 44), "TEK-UP SSIR 2026-2027", font=font(18), fill=GREY)
    draw.line((60, 78, W - 60, 78), fill=GOLD_BRIGHT, width=3)
    return img


def diagram(width: int, highlight: str | None = None) -> Image.Image:
    source = Image.open(BASE).convert("RGB")
    height = int(source.height * width / source.width)
    img = source.resize((width, height), Image.LANCZOS).convert("RGBA")
    if not highlight:
        return img.convert("RGB")
    zone = ZONES[highlight]
    dim = Image.new("RGBA", img.size, (255, 255, 255, 150))
    dimmed = Image.alpha_composite(img, dim)
    x0, y0, x1, y1 = zone["box"]
    box = (int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height))
    dimmed.paste(img.crop(box), box)
    draw = ImageDraw.Draw(dimmed)
    draw.rectangle(box, outline=zone["color"], width=6)
    label = zone["badge"]
    label_font = font(18, True)
    tw = draw.textbbox((0, 0), label, font=label_font)[2]
    chip_w = tw + 28
    chip_y = max(4, box[1] - 34)
    chip_x = box[2] - chip_w - 8 if highlight == "Z3" else box[0]
    draw.rounded_rectangle((chip_x, chip_y, chip_x + chip_w, chip_y + 30), radius=7, fill=zone["color"])
    draw.text((chip_x + 14, chip_y + 5), label, font=label_font, fill=WHITE)
    return dimmed.convert("RGB")


def caption(img: Image.Image, title: str | None, text: str) -> None:
    draw = ImageDraw.Draw(img)
    band_y = 970
    draw.rounded_rectangle((50, band_y, W - 50, 1060), radius=12, fill=NAVY)
    x = 80
    if title:
        draw.rectangle((80, band_y + 14, 86, 76), fill=GOLD_BRIGHT)
        draw.text((104, band_y + 20), title, font=font(21, True), fill=GOLD_BRIGHT)
        x = 104
        y = band_y + 48
        fnt = font(23)
    else:
        y = band_y + 24
        fnt = font(27)
    for line in wrap(draw, text, fnt, W - 190)[:2]:
        draw.text((x, y), line, font=fnt, fill=WHITE)
        y += fnt.size + 4


def slide_title() -> Image.Image:
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 18, H), fill=NAVY)
    draw.text((110, 100), "ARCHITECTURE DU PROJET", font=font(24, True), fill=GOLD)
    draw.text((110, 155), "Serveur MCP intelligent", font=font(66, True), fill=NAVY)
    draw.text((110, 235), "de Threat Intelligence", font=font(66, True), fill=NAVY)
    draw.line((112, 335, 920, 335), fill=GOLD_BRIGHT, width=4)
    draw.text((110, 365), "4 zones de confiance  ·  8 points de contrôle  ·  1 journal chaîné",
              font=font(30), fill=GOLD)
    draw.text((110, 440), "Mzabi Sirine  ·  Khaled Ellif", font=font(26, True), fill=INK)
    draw.text((110, 480), "TEK-UP SSIR 2026-2027  ·  encadrant : Tarek Hdji", font=font(22), fill=GREY)

    chips = [
        ("ZONE 0", "Poste analyste", BLUE, PALE_BLUE),
        ("ZONE 1", "Processus MCP", GREEN, PALE_GREEN),
        ("ZONE 2", "Données", GOLD, PALE_GOLD),
        ("ZONE 3", "Flux partenaires", RED, PALE_RED),
    ]
    for index, (badge, label, color, pale) in enumerate(chips):
        x = 110 + index * 430
        draw.rounded_rectangle((x, 670, x + 390, 830), radius=16, fill=pale, outline=color, width=3)
        draw.text((x + 24, 696), badge, font=font(20, True), fill=color)
        draw.text((x + 24, 738), label, font=font(28, True), fill=NAVY)
    draw.text((110, 885), "Le client ne parle jamais directement aux données.",
              font=font(26), fill=GREY)
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA")
        logo.thumbnail((210, 90))
        img.paste(logo, (W - 280, 60), logo)
    return img


def slide_overview() -> Image.Image:
    img = base_canvas()
    pic = diagram(1400)
    img.paste(pic, ((W - pic.width) // 2, 100))
    caption(img, None, "Le client ne parle jamais aux données : chaque requête traverse le processus MCP.")
    return img


def slide_zone(key: str, text: str) -> Image.Image:
    zone = ZONES[key]
    img = base_canvas()
    pic = diagram(1350, highlight=key)
    img.paste(pic, (50, 125))
    draw = ImageDraw.Draw(img)
    px, py, pw = 1425, 125, 445
    draw.rounded_rectangle((px, py, px + pw, py + 820), radius=16, fill=zone["fill"], outline=zone["color"], width=3)
    draw.text((px + 30, py + 28), zone["badge"], font=font(21, True), fill=zone["color"])
    draw.text((px + 30, py + 62), zone["title"], font=font(35, True), fill=NAVY)
    draw.line((px + 30, py + 112, px + pw - 30, py + 112), fill=zone["color"], width=2)
    y = py + 140
    bullet_font = font(19)
    for item in zone["bullets"]:
        draw.ellipse((px + 32, y + 10, px + 42, y + 20), fill=zone["color"])
        y = draw_paragraph(draw, (px + 56, y), item, bullet_font, INK, pw - 90, line_gap=5) + 18
    draw.text((px + 30, py + 735), "POINT DE CONTRÔLE", font=font(15, True), fill=GREY)
    draw.rounded_rectangle((px + 30, py + 760, px + pw - 30, py + 800), radius=8, fill=zone["color"])
    draw.text((px + 46, py + 770), zone["cp"], font=font(18, True), fill=WHITE)
    caption(img, None, text)
    return img


def slide_flow() -> Image.Image:
    img = base_canvas()
    draw = ImageDraw.Draw(img)
    draw.text((60, 110), "Le parcours d'une requête", font=font(40, True), fill=NAVY)
    draw.text((60, 165), "Huit étapes, huit points de contrôle nommés CP1 à CP8.", font=font(23), fill=GREY)
    steps = [
        ("1", "CP1", "Jeton signé", "HMAC-SHA256, porté par le client"),
        ("2", "CP1", "Authentification", "signature, expiration, posture"),
        ("3", "CP2", "Décision ABAC", "rôle, finalité, niveau, compartiments"),
        ("4", "CP3", "Appel d'outil", "schéma strict, lecture seule"),
        ("5", "CP4", "Assainissement", "injection neutralisée"),
        ("6", "CP5", "Enveloppe étiquetée", "niveau, TLP, masquage"),
        ("7", "CP6", "Limiteur de débit", "quota par client"),
        ("8", "CP7 · CP8", "Journal + réponse", "trace chaînée, sortie filtrée"),
    ]
    positions = []
    for index, (num, cp, title, detail) in enumerate(steps):
        col, row = index % 4, index // 4
        x = 70 + col * 455
        y = 250 + row * 300
        positions.append((x, y))
        color = GREEN if row == 0 else GOLD
        draw.rounded_rectangle((x, y, x + 410, y + 220), radius=16, fill=LIGHT, outline=color, width=3)
        draw.ellipse((x + 22, y + 22, x + 78, y + 78), fill=color)
        draw.text((x + 41, y + 33), num, font=font(26, True), fill=WHITE)
        draw.rounded_rectangle((x + 92, y + 26, x + 190, y + 62), radius=8, fill=color)
        draw.text((x + 104, y + 34), cp, font=font(16, True), fill=WHITE)
        draw.text((x + 22, y + 98), title, font=font(26, True), fill=NAVY)
        draw_paragraph(draw, (x + 22, y + 142), detail, font(18), GREY, 366, line_gap=4)
    # flèches horizontales et retour ligne
    for index in range(3):
        x, y = positions[index]
        draw.line((x + 415, y + 110, x + 448, y + 110), fill=GOLD_BRIGHT, width=6)
        draw.polygon([(x + 448, y + 102), (x + 464, y + 110), (x + 448, y + 118)], fill=GOLD_BRIGHT)
    for index in range(4, 7):
        x, y = positions[index]
        draw.line((x + 415, y + 110, x + 448, y + 110), fill=GOLD_BRIGHT, width=6)
        draw.polygon([(x + 448, y + 102), (x + 464, y + 110), (x + 448, y + 118)], fill=GOLD_BRIGHT)
    x4, y4 = positions[3]
    x5, y5 = positions[4]
    ymid = (y4 + 220 + y5) // 2
    draw.line((x4 + 205, y4 + 220, x4 + 205, ymid), fill=GOLD_BRIGHT, width=6)
    draw.line((x4 + 205, ymid, x5 + 205, ymid), fill=GOLD_BRIGHT, width=6)
    draw.line((x5 + 205, ymid, x5 + 205, y5 - 16), fill=GOLD_BRIGHT, width=6)
    draw.polygon([(x5 + 197, y5 - 16), (x5 + 213, y5 - 16), (x5 + 205, y5)], fill=GOLD_BRIGHT)
    caption(img, None, "Chaque flèche qui traverse une frontière est un point de contrôle nommé.")
    return img


def slide_outro() -> Image.Image:
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 18, H), fill=NAVY)
    draw.text((110, 110), "CE QU'IL FAUT RETENIR", font=font(24, True), fill=GOLD)
    draw.text((110, 165), "Une architecture vérifiable", font=font(58, True), fill=NAVY)
    metrics = [("4", "zones de confiance", BLUE), ("8", "points de contrôle", GREEN),
               ("1", "journal chaîné", GOLD), ("0", "accès direct aux données", RED)]
    for index, (value, label, color) in enumerate(metrics):
        x = 110 + index * 430
        draw.rounded_rectangle((x, 320, x + 390, 600), radius=18, fill=LIGHT, outline=color, width=3)
        draw.text((x + 30, 350), value, font=font(88, True), fill=color)
        draw_paragraph(draw, (x + 30, 480), label, font(25, True), NAVY, 330, line_gap=2)
    draw.text((110, 690), "Chaque refus, chaque accès et chaque contrôle laissent une trace.",
              font=font(30), fill=INK)
    draw.text((110, 745), "Architecture décrite au chapitre 4 ; contrôles testés dans le rapport.",
              font=font(24), fill=GREY)
    draw.line((112, 830, 1500, 830), fill=GOLD_BRIGHT, width=3)
    draw.text((110, 860), "TEK-UP SSIR 2026-2027  ·  Mzabi Sirine  ·  Khaled Ellif",
              font=font(22), fill=GREY)
    return img


def build_slides(work: Path) -> list[Path]:
    paths: list[Path] = []
    for index, slide in enumerate(SLIDES, start=1):
        if slide["kind"] == "title":
            img = slide_title()
        elif slide["kind"] == "overview":
            img = slide_overview()
        elif slide["kind"] == "zone":
            img = slide_zone(slide["zone"], slide["voice"])
        elif slide["kind"] == "flow":
            img = slide_flow()
        else:
            img = slide_outro()
        path = work / f"slide{index:02d}.png"
        img.save(path)
        paths.append(path)
    return paths


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    slides = build_slides(WORK)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        durations: list[float] = []
        voices: list[Path] = []
        for index, slide in enumerate(SLIDES, start=1):
            wav = tmp_path / f"voice{index:02d}.wav"
            subprocess.run(["pico2wave", "-l", "fr-FR", "-w", str(wav), slide["voice"]], check=True)
            vdur = float(subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(wav)], text=True).strip())
            durations.append(max(slide["min"], math.ceil((vdur + 1.6) * 2) / 2))
            voices.append(wav)
            print(f"slide {index}: voix {vdur:5.1f}s · durée {durations[-1]:5.1f}s")

        total = sum(durations)
        segments: list[Path] = []
        for index, (path, duration) in enumerate(zip(slides, durations), start=1):
            seg = tmp_path / f"seg{index:02d}.mp4"
            vf: list[str] = []
            if index == 1:
                vf.append("fade=t=in:st=0:d=0.6")
            if index == len(slides):
                vf.append(f"fade=t=out:st={max(0.0, duration - 1.0):.2f}:d=1.0")
            cmd = ["ffmpeg", "-y", "-loglevel", "error",
                   "-loop", "1", "-framerate", "25", "-t", f"{duration:.2f}", "-i", str(path)]
            if vf:
                cmd += ["-vf", ",".join(vf)]
            cmd += ["-r", "25", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", str(seg)]
            subprocess.run(cmd, check=True)
            segments.append(seg)

        video_only = tmp_path / "video.mp4"
        vlist = tmp_path / "segments.txt"
        vlist.write_text("".join(f"file '{seg}'\n" for seg in segments), encoding="utf-8")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(vlist), "-c", "copy", str(video_only)], check=True)

        inputs = ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
        for wav in voices:
            inputs += ["-i", str(wav)]
        filters = []
        labels = ["[0:a]"]
        offset = 0.6
        for index, wav in enumerate(voices, start=1):
            delay = int(offset * 1000)
            filters.append(f"[{index}:a]aresample=48000,adelay={delay}:all=1[a{index}]")
            labels.append(f"[a{index}]")
            offset += durations[index - 1]
        mix = "".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95[aout]"
        filters.append(mix)
        audio = tmp_path / "audio.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                        "-filter_complex", ";".join(filters), "-map", "[aout]", str(audio)], check=True)

        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_only), "-i", str(audio),
             "-t", f"{total:.2f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             "-movflags", "+faststart", str(OUT)],
            check=True,
        )
    print(f"VIDEO: {OUT}")
    print(f"DUREE: {total:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
