#!/usr/bin/env python3
"""Rend les preuves d'exécution en captures d'écran lisibles (PNG).

Les contenus proviennent uniquement de sorties réelles : la démonstration
`scripts/demo_defense.py` (preuves/logs/demo_capture.json) et la campagne de
tests (preuves/logs/tests_latest.json). Aucune valeur n'est inventée ici.
"""
from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parents[1]
DEMO_JSON = PROJECT / "preuves" / "logs" / "demo_capture.json"
DEMO_TXT = PROJECT / "preuves" / "logs" / "demo_transcript.txt"
TESTS = PROJECT / "preuves" / "logs" / "tests_latest.json"
OUT = PROJECT / "preuves" / "captures"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

BG = "#0b1020"
BAR = "#161d31"
FG = "#e6edf7"
DIM = "#8b98b8"
GREEN = "#7ee787"
AMBER = "#f2cc60"
RED = "#ff7b72"
CYAN = "#79c0ff"
VIOLET = "#d2a8ff"
WHITE = "#ffffff"

FONT = ImageFont.truetype(str(FONT_DIR / "DejaVuSansMono.ttf"), 19)
FONT_BOLD = ImageFont.truetype(str(FONT_DIR / "DejaVuSansMono-Bold.ttf"), 19)
FONT_TITLE = ImageFont.truetype(str(FONT_DIR / "DejaVuSans-Bold.ttf"), 22)
FONT_SMALL = ImageFont.truetype(str(FONT_DIR / "DejaVuSansMono.ttf"), 14)

WIDTH = 1560
PAD = 30
LINE_H = 28


def color_for(line: str) -> tuple[str, ImageFont.FreeTypeFont]:
    stripped = line.strip()
    if not stripped:
        return FG, FONT
    if stripped.startswith("S") and "—" in stripped and stripped[1:3].strip().isdigit():
        return CYAN, FONT_BOLD
    if stripped.startswith("$"):
        return GREEN, FONT
    if stripped.startswith(">"):
        return AMBER, FONT
    if stripped.startswith("•"):
        return WHITE, FONT
    lowered = stripped.lower()
    if "échec" in lowered or "iserror=true" in lowered or "present=false" in lowered.replace("présent", "present"):
        return RED, FONT
    if any(token in stripped for token in ("valide=True", "OK", "autorisé", "lecture seule", "True")):
        return GREEN, FONT
    if "canari" in lowered or "reason=" in lowered or "journal" in lowered:
        return VIOLET, FONT
    if stripped.startswith("Tests:") or stripped.startswith("Détection") or stripped.startswith("Latence"):
        return GREEN, FONT_BOLD
    return FG, FONT


def wrap(line: str) -> list[str]:
    if not line:
        return [""]
    width_chars = int((WIDTH - 2 * PAD) / (FONT.getlength("M")))
    parts = textwrap.wrap(line, width=width_chars, subsequent_indent="    ",
                          replace_whitespace=False, drop_whitespace=False)
    return parts or [""]


def render(path: Path, title: str, subtitle: str, lines: Iterable[str], footer: str) -> None:
    wrapped: list[tuple[str, str, ImageFont.FreeTypeFont]] = []
    for raw in lines:
        for chunk in wrap(raw):
            color, font = color_for(chunk)
            wrapped.append((chunk, color, font))

    height = 56 + PAD + len(wrapped) * LINE_H + 118
    image = Image.new("RGB", (WIDTH, height), BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, WIDTH, 46], radius=0, fill=BAR)
    for index, color in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        draw.ellipse([22 + index * 26, 16, 36 + index * 26, 30], fill=color)
    draw.text((WIDTH / 2, 23), "terminal — tekup-mcp-ti", font=FONT_SMALL, fill=DIM, anchor="mm")
    draw.text((PAD, 66), title, font=FONT_TITLE, fill=WHITE)
    draw.text((PAD, 98), subtitle, font=FONT_SMALL, fill=DIM)

    y = 136
    for chunk, color, font in wrapped:
        draw.text((PAD, y), chunk, font=font, fill=color)
        y += LINE_H

    draw.line([(PAD, height - 56), (WIDTH - PAD, height - 56)], fill="#25304a", width=1)
    draw.text((PAD, height - 38), footer, font=FONT_SMALL, fill=DIM)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG", optimize=True)
    print(f"[capture] {path.relative_to(PROJECT)} ({WIDTH}x{height})")


def scenes_from_text() -> dict[str, list[str]]:
    scenes: dict[str, list[str]] = {}
    current: str | None = None
    for line in DEMO_TXT.read_text(encoding="utf-8").splitlines():
        if line.startswith("S") and "—" in line and line[1:3].strip().isdigit():
            current = line.split("—", 1)[0].strip()
            scenes[current] = [line]
        elif current:
            scenes[current].append(line)
    return scenes


def capture_tests() -> None:
    data = json.loads(TESTS.read_text(encoding="utf-8"))
    resume = data["resume"]
    metrics = data["metriques"]
    latency = metrics["latence"]
    audit = metrics["audit"]
    hardening = metrics["durcissement"]
    lines = [
        "$ python3 tests/run_tests.py",
        "",
        f"Tests: {resume['reussis']}/{resume['tests']} — échecs: {resume['echecs']} "
        f"(nominaux {resume['nominaux']}, abus {resume['abus']})",
        f"Détection abus: {metrics['abus_detectes']}/{metrics['abus_total']} "
        f"({metrics['taux_detection_abus_pct']} %)",
        f"Latence p95: {latency['p95_ms']} ms (n={latency['n']})  "
        f"p50={latency['p50_ms']} ms  p99={latency['p99_ms']} ms",
        f"Audit: valide={audit['valide']}  entrées={audit['entrees']}  "
        f"appels attendus={audit['appels_attendus']}  complétude={audit['completude_pct']} %",
        f"Révocation: commande={metrics['revocation']['commande_ms']} ms  "
        f"application={metrics['revocation']['requete_suivante_ms']} ms  "
        f"audit={metrics['revocation']['audit']}",
        f"Injection: {metrics['injection']['malveillants_detectes']}/"
        f"{metrics['injection']['malveillants_total']} détectés  "
        f"faux positifs={metrics['injection']['faux_positifs_unitaire']}",
        "",
        "Extraits de la campagne :",
    ]
    wanted = {"A06", "A07", "A10", "A14", "A15", "A16"}
    for case in data["tests"]:
        if case["id"] in wanted:
            mark = "OK" if case["reussi"] else "ÉCHEC"
            lines.append(f"  [{mark:>4}] {case['id']} {case['titre']} — {case['obtenu']}")
    lines += [
        "",
        f"Durcissement: uid={hardening['uid_execution']} ({hardening['utilisateur']})  "
        f"base={hardening['db_mode']}  clé={hardening['key_mode']}  "
        f"écriture refusée={hardening['ecriture_base_refusee']}",
        f"Comparatif: maquette {metrics['comparatif_avant_apres']['maquette']['faiblesses']}/8 faiblesses ; "
        f"serveur durci {metrics['comparatif_avant_apres']['serveur_durci']['faiblesses']} faiblesse",
    ]
    render(
        OUT / "cap_07_campagne_tests.png",
        "Capture 7 — Campagne de tests bout en bout",
        "31 scénarios exécutés dans le laboratoire, résultats consignés sans filtrage",
        lines,
        f"Source : preuves/logs/tests_latest.json · exécuté le {data['date'][:19].replace('T', ' ')} UTC",
    )


def main() -> int:
    demo = json.loads(DEMO_JSON.read_text(encoding="utf-8"))
    scenes = scenes_from_text()
    stamp = demo["genere_le"][:19].replace("T", " ")
    footer = f"Source : preuves/logs/demo_capture.json · laboratoire isolé · exécuté le {stamp} UTC"

    render(
        OUT / "cap_01_outils.png",
        "Capture 1 — Découverte du serveur MCP",
        "initialize, tools/list et ti_health avec un jeton analyste",
        scenes.get("S1", []),
        footer,
    )
    render(
        OUT / "cap_02_fuite_bloquee.png",
        "Capture 2 — Fuite tentée puis bloquée",
        "Deux jetons différents, deux refus génériques, deux traces d'audit distinctes",
        scenes.get("S2", []) + [""] + scenes.get("S3", []),
        footer,
    )
    render(
        OUT / "cap_03_acces_autorise.png",
        "Capture 3 — Accès Secret autorisé et contrôlé",
        "Le même bulletin, cette fois avec l'habilitation et le compartiment requis",
        scenes.get("S4", []),
        footer,
    )
    render(
        OUT / "cap_04_injection.png",
        "Capture 4 — Injection d'instructions neutralisée",
        "Le contenu hostile est livré comme donnée inerte et signalé dans l'audit",
        scenes.get("S5", []),
        footer,
    )
    render(
        OUT / "cap_05_audit.png",
        "Capture 5 — Chaîne d'audit vérifiée",
        "Chaque décision est chaînée par empreinte ; toute rupture est détectable",
        scenes.get("S6", []),
        footer,
    )
    render(
        OUT / "cap_06_avant_apres.png",
        "Capture 6 — Avant / après sur les mêmes bulletins",
        "Maquette sans contrôle contre serveur durci, à jeu de données identique",
        scenes.get("S7", []),
        footer,
    )

    hardening = json.loads(TESTS.read_text(encoding="utf-8"))["metriques"]["durcissement"]
    lines = [
        "$ " + hardening["commande"],
        "",
        f"  utilisateur effectif : {hardening['utilisateur']} (uid={hardening['uid_execution']})",
        f"  base SQLite         : {hardening['db_mode']} (lecture seule pour le service)",
        f"  clé de signature    : {hardening['key_mode']} (propriétaire uniquement)",
        f"  journal d'audit     : écriture={hardening['audit_ecrit']}",
        f"  tentative d'écriture en base : refusée={hardening['ecriture_base_refusee']}",
        "",
        "  Le serveur tourne sans privilège ; une compromission du processus",
        "  ne donne ni la base en écriture, ni la clé, ni les droits du poste.",
    ]
    render(
        OUT / "cap_08_durcissement.png",
        "Capture 8 — Exécution sans privilège",
        "Le service est lancé sous l'utilisateur nobody avec des fichiers en lecture seule",
        lines,
        f"Source : preuves/logs/tests_latest.json · scénario N15 · commande setpriv",
    )

    capture_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
