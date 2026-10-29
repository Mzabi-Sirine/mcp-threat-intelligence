"""Régression : la relecture de la queue du journal ne doit pas couper un caractère UTF-8.

Reproduit le cas où size-8192 tombe entre les deux octets d'un « é » (0xC3 0xA9).
Avant correctif : UnicodeDecodeError 0xA9 position 0. Après : append réussit, seq=2.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ti_server.audit import AuditLog


def build_file(path: Path) -> None:
    pad = None
    for n in range(8000, 8400):
        candidate = json.dumps({"seq": 1, "entry_hash": "abc", "pad": "a" * n}, separators=(",", ":"))
        if len(candidate.encode()) == 8189:
            pad = "a" * n
            break
    if pad is None:
        raise RuntimeError("calage impossible")
    line = json.dumps({"seq": 1, "entry_hash": "abc", "pad": pad}, separators=(",", ":"))
    path.write_bytes("é\n".encode() + line.encode() + b"\n")


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        build_file(path)
        start = path.stat().st_size - 8192
        assert path.read_bytes()[start] == 0xA9, "le cas frontière n'est pas reproduit"
        entry = AuditLog(path).append("TEST_REGRESSION", detail="frontière UTF-8")
        assert entry["seq"] == 2, entry
        assert entry["prev_hash"] == "abc", entry
    print("[OK ] queue de journal alignée : append après frontière UTF-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
