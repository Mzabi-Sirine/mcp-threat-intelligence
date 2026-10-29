#!/usr/bin/env python3
"""Enregistre la démonstration réelle dans un MP4 1280x720.

Xvfb + xterm + ffmpeg x11grab : le terminal joue scripts/demo_defense.py en mode
présentation, avec une pause automatique entre les sept scènes.
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "preuves" / "video" / "Demo_MCP_Threat_Intelligence.mp4"
RAW = PROJECT / "preuves" / "video" / "demo_raw.mp4"
DISPLAY = ":99"
WATERMARK = "TEK-UP SSIR - MCP Threat Intelligence"


def main() -> int:
    parser = argparse.ArgumentParser(description="Enregistre la démo en MP4.")
    parser.add_argument("--delay", type=float, default=17.0, help="secondes entre les scènes")
    args = parser.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pkill", "-x", "Xvfb"], check=False)
    subprocess.run(["pkill", "-x", "xterm"], check=False)
    time.sleep(0.5)

    xvfb = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", "1600x900x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.2)
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "x11grab", "-draw_mouse", "0",
         "-video_size", "1600x900", "-framerate", "25", "-i", f"{DISPLAY}.0",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
         str(RAW)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(0.8)
    xterm = subprocess.Popen(
        ["xterm", "-display", DISPLAY, "-geometry", "122x36+40+40",
         "-fa", "DejaVu Sans Mono", "-fs", "15",
         "-bg", "#0b0f14", "-fg", "#e6edf3", "-bw", "0", "-b", "0",
         "-title", "Démonstration MCP Threat Intelligence",
         "-e", "bash", "scripts/demo_video.sh", str(args.delay)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    code = xterm.wait()
    time.sleep(1.0)
    ffmpeg.send_signal(signal.SIGINT)
    ffmpeg.wait(timeout=15)
    xvfb.terminate()
    xvfb.wait(timeout=5)

    if not RAW.exists() or RAW.stat().st_size < 100_000:
        print("Échec : enregistrement brut absent ou vide.", file=sys.stderr)
        return 1

    probe = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(RAW)],
        text=True,
    )
    duration = float(probe.strip())
    fade_out = max(0.0, duration - 1.2)
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    filters = (
        "fade=t=in:st=0:d=0.7,"
        f"fade=t=out:st={fade_out:.2f}:d=1.2,"
        f"drawtext=fontfile={font}:text='{WATERMARK}':x=w-tw-24:y=h-32:"
        "fontsize=14:fontcolor=0x7A8899"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(RAW), "-vf", filters,
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)],
        check=True,
    )
    RAW.unlink(missing_ok=True)
    print(f"VIDEO: {OUT}")
    print(f"DUREE: {duration:.1f} s · scenes: 7 · xterm code: {code}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
