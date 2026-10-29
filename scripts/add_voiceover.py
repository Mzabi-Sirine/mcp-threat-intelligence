#!/usr/bin/env python3
"""Ajoute une voix off française à la vidéo de démonstration."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
VIDEO = PROJECT / "preuves" / "video" / "Demo_MCP_Threat_Intelligence.mp4"
OUT = PROJECT / "preuves" / "video" / "Demo_MCP_Threat_Intelligence_voix.mp4"

SEGMENTS = [
    (1.0, "Démonstration du serveur MCP de Threat Intelligence, projet TEK-UP SSIR."),
    (7.3, "Le serveur démarre en local et expose six outils en lecture seule. "
          "Il découvre le jeu de données synthétique."),
    (22.7, "Une analyste Confidentiel demande un bulletin Secret. "
           "Le serveur refuse, et le canari de contrôle reste absent."),
    (38.1, "Un agent Secret, sans le compartiment CRYPTO, demande le même bulletin. "
           "Refus : le besoin d'en connaître est vérifié séparément."),
    (53.5, "Avec Secret et CRYPTO, l'accès est autorisé. "
           "Le canari apparaît : le contrôle positif fonctionne."),
    (68.9, "Un bulletin partenaire contient une instruction hostile. "
           "Elle est signalée, neutralisée et journalisée, jamais exécutée."),
    (84.3, "Le journal est chaîné. Après le journal valide, une copie falsifiée est détectée : "
           "la rupture est localisée."),
    (99.7, "Même bulletin, deux serveurs. La maquette laisse fuiter le canari et la source ; "
           "le serveur durci masque, refuse et journalise."),
    (109.2, "Chaque refus et chaque accès laissent une trace chaînée. Fin de la démonstration."),
]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inputs: list[str] = ["-i", str(VIDEO)]
        filters: list[str] = []
        labels: list[str] = []
        for index, (start, text) in enumerate(SEGMENTS, start=1):
            wav = tmp_path / f"seg{index}.wav"
            subprocess.run(["pico2wave", "-l", "fr-FR", "-w", str(wav), text], check=True)
            duration = float(subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(wav)], text=True).strip())
            print(f"segment {index}: {duration:5.1f} s  début {start:5.1f} s  fin {start + duration:5.1f} s")
            inputs += ["-i", str(wav)]
            delay = int(start * 1000)
            filters.append(f"[{index}:a]aresample=48000,adelay={delay}:all=1[a{index}]")
            labels.append(f"[a{index}]")
        mix = "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0,alimiter=limit=0.95[aout]"
        filters.append(mix)
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", *inputs,
             "-filter_complex", ";".join(filters),
             "-map", "0:v", "-map", "[aout]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
             "-movflags", "+faststart", str(OUT)],
            check=True,
        )
    print(f"VIDEO: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
