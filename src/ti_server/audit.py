"""Journal d'audit append-only à chaîne de hachage (point unique)."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import iso, utcnow

GENESIS = "0" * 64


class AuditError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_args(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def entry_hash(prev_hash: str, entry: dict[str, Any]) -> str:
    material = dict(entry)
    material.pop("entry_hash", None)
    return hashlib.sha256(prev_hash.encode("ascii") + canonical(material)).hexdigest()


@dataclass
class VerifyResult:
    ok: bool
    entries: int
    broken_at: int | None = None
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "entries": self.entries, "broken_at": self.broken_at, "reason": self.reason}


class AuditLog:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch(mode=0o640)
        os.chmod(self.path, 0o640)

    def _last(self, handle) -> tuple[int, str]:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        if size == 0:
            return 0, GENESIS
        start = max(0, size - 8192)
        handle.seek(start)
        chunk = handle.read()
        if start > 0:
            cut = chunk.find(b"\n")
            if cut < 0:
                handle.seek(0)
                chunk = handle.read()
            else:
                chunk = chunk[cut + 1:]
        lines = [line for line in chunk.split(b"\n") if line.strip()]
        if not lines:
            return 0, GENESIS
        try:
            last = json.loads(lines[-1].decode("utf-8"))
            return int(last["seq"]), str(last["entry_hash"])
        except Exception as exc:
            raise AuditError("queue de journal illisible") from exc

    def append(self, event: str, **fields: Any) -> dict[str, Any]:
        payload = {
            "ts": iso(utcnow()),
            "event": event,
        }
        payload.update(fields)
        try:
            with open(self.path, "a+b") as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                handle.seek(0, os.SEEK_END)
                seq, prev = self._last(handle)
                entry = {"seq": seq + 1, "prev_hash": prev, **payload}
                entry["entry_hash"] = entry_hash(prev, entry)
                handle.write((json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
                handle.flush()
                os.fsync(handle.fileno())
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                return entry
        except OSError as exc:
            raise AuditError(f"écriture d'audit impossible: {exc}") from exc

    def verify(self) -> VerifyResult:
        prev = GENESIS
        expected_seq = 1
        count = 0
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                for raw in handle:
                    raw = raw.strip()
                    if not raw:
                        continue
                    count += 1
                    try:
                        entry = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        return VerifyResult(False, count, expected_seq, f"JSON invalide: {exc}")
                    if int(entry.get("seq", -1)) != expected_seq:
                        return VerifyResult(False, count, expected_seq, "séquence non contiguë")
                    if entry.get("prev_hash") != prev:
                        return VerifyResult(False, count, expected_seq, "chaînage rompu")
                    stored = entry.get("entry_hash")
                    recomputed = entry_hash(prev, entry)
                    if stored != recomputed:
                        return VerifyResult(False, count, expected_seq, "empreinte invalide")
                    prev = stored
                    expected_seq += 1
        except FileNotFoundError:
            return VerifyResult(False, 0, None, "journal absent")
        return VerifyResult(True, count)

    def tail(self, limit: int = 20) -> list[dict[str, Any]]:
        lines: list[str] = []
        with open(self.path, "r", encoding="utf-8") as handle:
            for raw in handle:
                if raw.strip():
                    lines.append(raw)
        return [json.loads(line) for line in lines[-limit:]]
