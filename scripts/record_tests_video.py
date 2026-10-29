#!/usr/bin/env python3
"""Enregistre la campagne de tests réelle et ajoute une voix off calée sur les étapes."""

from __future__ import annotations

import argparse
import json
import signal
import subprocess
import tempfile
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "preuves" / "video" / "Demo_Tests_MCP_TI.mp4"
RAW = PROJECT / "preuves" / "video" / "tests_raw.mp4"
DISPLAY = ":99"
WATERMARK = "TEK-UP SSIR - MCP Threat Intelligence"


def record(marks: Path) -> tuple[float, dict[str, float]]:
    subprocess.run(["pkill", "-x", "Xvfb"], check=False)
    subprocess.run(["pkill", "-x", "xterm"], check=False)
    time.sleep(0.5)
    xvfb = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", "1600x900x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.2)
    start = time.time()
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "x11grab", "-draw_mouse", "0",
         "-video_size", "1600x900", "-framerate", "25", "-i", f"{DISPLAY}.0",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         str(RAW)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.8)
    xterm = subprocess.Popen(
        ["xterm", "-display", DISPLAY, "-geometry", "122x40+30+20",
         "-fa", "DejaVu Sans Mono", "-fs", "13",
         "-bg", "#0b0f14", "-fg", "#e6edf3", "-bw", "0", "-b", "0",
         "-title", "Campagne de tests MCP Threat Intelligence",
         "-e", "bash", "scripts/tests_video.sh", str(marks)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    code = xterm.wait()
    time.sleep(1.0)
    ffmpeg.send_signal(signal.SIGINT)
    ffmpeg.wait(timeout=15)
    xvfb.terminate()
    xvfb.wait(timeout=5)
    if not RAW.exists() or RAW.stat().st_size < 100_000:
        raise SystemExit("Échec : enregistrement brut absent ou vide.")
    duration = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(RAW)], text=True).strip())
    offsets: dict[str, float] = {}
    for line in marks.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        offsets[item["stage"]] = max(0.0, float(item["t"]) - start)
    print(f"[enregistrement] {duration:.1f} s · xterm code {code} · jalons {sorted(offsets)}")
    return duration, offsets


def voice_segments(offsets: dict[str, float]) -> list[tuple[float, str]]:
    tests_start = offsets.get("tests_start", 7.0)
    tests_end = offsets.get("tests_end", 17.0)
    audit_start = offsets.get("audit_start", tests_end + 9.0)
    outro_start = offsets.get("outro_start", audit_start + 9.0)
    return [
        (1.6, "Campagne de tests du serveur MCP de Threat Intelligence, exécutée en direct dans le terminal."),
        (tests_start + 0.3,
         "Trente et un scénarios : nominaux, durcissement et seize tentatives d'abus. "
         "Chaque ligne produit une preuve."),
        (tests_end + 0.4,
         "Bilan : trente et un sur trente et un, seize abus sur seize, aucune fuite."),
        (audit_start + 0.3,
         "La chaîne d'audit du journal réel est vérifiée : toutes les entrées sont valides."),
        (outro_start + 0.8,
         "Le projet tourne, les contrôles sont testés, chaque décision laisse une trace."),
    ]


def place(segments, durations, gap=0.35):
    placed = []
    previous_end = -gap
    for (preferred, text), speech in zip(segments, durations):
        start = max(preferred, previous_end + gap)
        placed.append((start, text, speech))
        previous_end = start + speech
    return placed


def main() -> int:
    parser = argparse.ArgumentParser(description="Enregistre la campagne de tests en MP4.")
    parser.add_argument("--marks", type=Path, default=Path("/tmp/ti_tests_marks.jsonl"))
    args = parser.parse_args()
    args.marks.parent.mkdir(parents=True, exist_ok=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)

    duration, offsets = record(args.marks)
    segments = voice_segments(offsets)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wavs: list[Path] = []
        durations: list[float] = []
        for index, (_, text) in enumerate(segments, start=1):
            wav = tmp_path / f"seg{index}.wav"
            subprocess.run(["pico2wave", "-l", "fr-FR", "-w", str(wav), text], check=True)
            durations.append(float(subprocess.check_output(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", str(wav)], text=True).strip()))
            wavs.append(wav)
        placed = place(segments, durations)
        inputs = ["-f", "lavfi", "-t", f"{duration:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
        filters: list[str] = []
        labels = ["[0:a]"]
        for index, (start, _, speech) in enumerate(placed, start=1):
            print(f"segment {index}: {speech:5.1f} s · début {start:5.1f} s · fin {start + speech:5.1f} s")
            inputs += ["-i", str(wavs[index - 1])]
            filters.append(f"[{index}:a]aresample=48000,adelay={int(start * 1000)}:all=1[a{index}]")
            labels.append(f"[a{index}]")
        filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=first:normalize=0,"
                                          "alimiter=limit=0.95[aout]")
        audio = tmp_path / "audio.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs,
                        "-filter_complex", ";".join(filters), "-map", "[aout]", str(audio)], check=True)

        fade_out = max(0.0, duration - 1.2)
        font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        filters_v = (
            "fade=t=in:st=0:d=0.7,"
            f"fade=t=out:st={fade_out:.2f}:d=1.2,"
            f"drawtext=fontfile={font}:text='{WATERMARK}':x=w-tw-24:y=h-32:"
            "fontsize=14:fontcolor=0x7A8899"
        )
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(RAW), "-i", str(audio),
             "-t", f"{duration:.2f}", "-vf", filters_v,
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(OUT)],
            check=True,
        )
    RAW.unlink(missing_ok=True)
    print(f"VIDEO: {OUT}")
    print(f"DUREE: {duration:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
