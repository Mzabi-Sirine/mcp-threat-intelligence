#!/usr/bin/env python3
"""Capture de vraies fenêtres xterm exécutant le projet (Xvfb + xwd).

Chaque scène lance un xterm sur un serveur X virtuel, exécute les commandes
du projet, puis capture la fenêtre avec xwd. Aucune image n'est téléchargée.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "preuves" / "captures_ecran"
DISPLAY = ":99"
BG = (11, 16, 32)

P = r"""p() { printf '\n\033[1;32mti@lab\033[0m:\033[1;34m~/tekup-mcp-ti\033[0m$ '; }
"""

SCENES = [
    (
        "01_environnement_donnees",
        P
        + r"""clear
p; printf '%s\n' 'pwd && ls'
pwd; echo; ls
p; printf '%s\n' 'python3 --version && python3 -c "import sqlite3; print(sqlite3.sqlite_version)"'
python3 --version
python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
p; printf '%s\n' 'PYTHONPATH=src python3 src/ti_cli.py stats'
PYTHONPATH=src python3 src/ti_cli.py stats
sleep 120
""",
    ),
    (
        "02_interface_mcp_six_outils",
        P
        + r"""clear
p; printf '%s\n' "python3 scripts/demo_defense.py | sed -n '5,16p'"
python3 scripts/demo_defense.py | sed -n '5,16p'
sleep 120
""",
    ),
    (
        "03_fuites_bloquees",
        P
        + r"""clear
p; printf '%s\n' "python3 scripts/demo_defense.py | sed -n '19,31p'"
python3 scripts/demo_defense.py | sed -n '19,31p'
sleep 120
""",
    ),
    (
        "04_acces_et_injection",
        P
        + r"""clear
p; printf '%s\n' "python3 scripts/demo_defense.py | sed -n '32,45p'"
python3 scripts/demo_defense.py | sed -n '32,45p'
sleep 120
""",
    ),
    (
        "05_audit_falsification",
        P
        + r"""clear
p; printf '%s\n' 'python3 src/ti_cli.py verify-audit --path preuves/lab/audit.jsonl'
python3 src/ti_cli.py verify-audit --path preuves/lab/audit.jsonl
p; printf '%s\n' 'python3 src/ti_cli.py verify-audit --path preuves/lab/audit_falsifie.jsonl'
python3 src/ti_cli.py verify-audit --path preuves/lab/audit_falsifie.jsonl
sleep 120
""",
    ),
    (
        "06_avant_apres",
        P
        + r"""clear
p; printf '%s\n' "python3 scripts/demo_defense.py | sed -n '53,60p'"
python3 scripts/demo_defense.py | sed -n '53,60p'
sleep 120
""",
    ),
    (
        "07_moindre_privilege",
        P
        + r"""clear
R=/tmp/ti-nonroot
rm -rf $R; mkdir -p $R/src $R/data $R/audit
cp -r src/ti_server $R/src/
cp preuves/lab/ti.db preuves/lab/token.key $R/data/
chown -R nobody:nogroup $R/data $R/audit
chmod 550 $R/data; chmod 440 $R/data/ti.db; chmod 400 $R/data/token.key; chmod 700 $R/audit
p; printf '%s\n' 'stat -c "%a %U:%G %n" $R/data/ti.db $R/data/token.key'
stat -c '%a %U:%G %n' $R/data/ti.db $R/data/token.key
p; printf '%s\n' 'setpriv --reuid=65534 --regid=65534 --clear-groups python3 -c "print(os.getuid())"'
setpriv --reuid=65534 --regid=65534 --clear-groups /usr/bin/python3 -c 'import os; print("uid =", os.getuid())'
p; printf '%s\n' 'setpriv ... python3 -c "open(ti.db, O_WRONLY|O_APPEND)"'
TI_DB=$R/data/ti.db setpriv --reuid=65534 --regid=65534 --clear-groups /usr/bin/python3 -c 'import os; os.open(os.environ["TI_DB"], os.O_WRONLY | os.O_APPEND)' 2>&1 | tail -1
sleep 120
""",
    ),
]


def crop(path: Path) -> None:
    image = Image.open(path).convert("RGB")
    pixels = image.load()
    width, height = image.size
    min_x, min_y, max_x, max_y = width, height, -1, -1
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[x, y]
            if abs(r - BG[0]) + abs(g - BG[1]) + abs(b - BG[2]) > 18:
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)
    if max_x < 0:
        return
    pad = 12
    box = (max(0, min_x - pad), max(0, min_y - pad),
           min(width, max_x + pad + 1), min(height, max_y + pad + 1))
    image.crop(box).save(path, "PNG", optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pkill", "-x", "Xvfb"], check=False)
    subprocess.run(["pkill", "-x", "xterm"], check=False)
    time.sleep(0.5)
    xvfb = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", "1600x1100x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    env = dict(os.environ, DISPLAY=DISPLAY)
    tmp = Path(tempfile.mkdtemp(prefix="ti-scenes-"))
    try:
        for name, body in SCENES:
            script = tmp / f"{name}.sh"
            script.write_text("#!/bin/bash\ncd /root/tekup-mcp-ti\n" + body, encoding="utf-8")
            script.chmod(0o755)
            term = subprocess.Popen(
                ["xterm", "-fa", "DejaVu Sans Mono", "-fs", "14",
                 "-geometry", "112x44+0+0", "-bg", "#0b1020", "-fg", "#e6edf7",
                 "-b", "2", "-xrm", "XTerm*scrollBar:false",
                 "-T", "TEK-UP - projet MCP", "-e", "/bin/bash", str(script)],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            time.sleep(4.5)
            xwd = tmp / f"{name}.xwd"
            subprocess.run(["xwd", "-root", "-silent", "-out", str(xwd)],
                           env=env, check=True, timeout=20)
            png = OUT / f"{name}.png"
            subprocess.run(["convert", str(xwd), "-trim", "+repage", str(png)],
                           check=True, timeout=30)
            crop(png)
            term.terminate()
            term.wait(timeout=10)
            print(f"[capture] {png.relative_to(PROJECT)}  {Image.open(png).size}")
            time.sleep(0.6)
    finally:
        xvfb.terminate()
        xvfb.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree("/tmp/ti-nonroot", ignore_errors=True)


if __name__ == "__main__":
    main()
