"""Persistance SQLite et ingestion contrôlée des flux synthétiques."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any
from urllib.parse import quote

from . import sanitize
from .config import DATA_DIR, DB_PATH, label_name, parse_ts, tlp_name, utcnow, iso
from .labels import parse_level, normalize_compartment

SCHEMA = """
CREATE TABLE IF NOT EXISTS advisories (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    body TEXT NOT NULL,
    classification INTEGER NOT NULL CHECK (classification BETWEEN 0 AND 3),
    compartments TEXT NOT NULL,
    source TEXT NOT NULL,
    source_trust REAL NOT NULL,
    published_at TEXT NOT NULL,
    cvss REAL NOT NULL,
    epss REAL NOT NULL,
    kev INTEGER NOT NULL,
    products TEXT NOT NULL,
    source_identity TEXT,
    canary TEXT,
    injection_flags TEXT NOT NULL,
    original_sha256 TEXT NOT NULL,
    advisory_type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS iocs (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    family TEXT NOT NULL,
    tags TEXT NOT NULL,
    confidence REAL NOT NULL,
    first_seen TEXT NOT NULL,
    classification INTEGER NOT NULL CHECK (classification BETWEEN 0 AND 3),
    compartments TEXT NOT NULL,
    source TEXT NOT NULL,
    advisory_ids TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    criticality INTEGER NOT NULL,
    exposure INTEGER NOT NULL,
    classification INTEGER NOT NULL CHECK (classification BETWEEN 0 AND 3),
    compartments TEXT NOT NULL,
    products TEXT NOT NULL,
    owner TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revoked (
    jti TEXT PRIMARY KEY,
    revoked_at TEXT NOT NULL,
    reason TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ioc_value ON iocs(value);
CREATE INDEX IF NOT EXISTS idx_ioc_family ON iocs(family);
"""


class StoreError(RuntimeError):
    pass


def _json_table(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class Store:
    def __init__(self, path: Path | str = DB_PATH, read_only: bool = True):
        self.path = Path(path)
        self.read_only = read_only
        if not self.path.exists():
            raise StoreError(f"base absente: {self.path}")

    def _connect(self) -> sqlite3.Connection:
        if self.read_only:
            uri = f"file:{quote(self.path.resolve().as_posix(), safe='/')}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=5.0)
            conn.execute("PRAGMA query_only=ON")
        else:
            conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _advisory(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["compartments"] = json.loads(item["compartments"])
        item["products"] = json.loads(item["products"])
        item["injection_flags"] = json.loads(item["injection_flags"])
        item["kev"] = bool(item["kev"])
        item["classification_name"] = label_name(item["classification"])
        item["tlp"] = tlp_name(item["classification"])
        return item

    @staticmethod
    def _ioc(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["tags"] = json.loads(item["tags"])
        item["compartments"] = json.loads(item["compartments"])
        item["advisory_ids"] = json.loads(item["advisory_ids"])
        item["classification_name"] = label_name(item["classification"])
        item["tlp"] = tlp_name(item["classification"])
        return item

    @staticmethod
    def _asset(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["compartments"] = json.loads(item["compartments"])
        item["products"] = json.loads(item["products"])
        item["classification_name"] = label_name(item["classification"])
        item["tlp"] = tlp_name(item["classification"])
        return item

    def get_advisory(self, advisory_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM advisories WHERE id = ?", (advisory_id,)).fetchone()
        return self._advisory(row) if row else None

    def all_advisories(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM advisories ORDER BY id").fetchall()
        return [self._advisory(row) for row in rows]

    def get_ioc(self, value: str, ioc_type: str | None = None) -> dict[str, Any] | None:
        sql = "SELECT * FROM iocs WHERE lower(value) = lower(?)"
        params: list[Any] = [value]
        if ioc_type:
            sql += " AND type = ?"
            params.append(ioc_type)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return self._ioc(row) if row else None

    def all_iocs(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM iocs ORDER BY id").fetchall()
        return [self._ioc(row) for row in rows]

    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
        return self._asset(row) if row else None

    def all_assets(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM assets ORDER BY id").fetchall()
        return [self._asset(row) for row in rows]

    def is_revoked(self, jti: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM revoked WHERE jti = ?", (jti,)).fetchone()
        return bool(row)

    def revoke(self, jti: str, reason: str) -> None:
        if self.read_only:
            raise StoreError("base en lecture seule")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO revoked(jti, revoked_at, reason) VALUES (?, ?, ?)",
                (jti, iso(utcnow()), reason),
            )
            conn.commit()

    def list_revoked(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM revoked ORDER BY revoked_at DESC").fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            advisories = conn.execute("SELECT count(*) FROM advisories").fetchone()[0]
            iocs = conn.execute("SELECT count(*) FROM iocs").fetchone()[0]
            assets = conn.execute("SELECT count(*) FROM assets").fetchone()[0]
            revoked = conn.execute("SELECT count(*) FROM revoked").fetchone()[0]
            by_level = conn.execute(
                "SELECT classification, count(*) FROM advisories GROUP BY classification ORDER BY classification"
            ).fetchall()
        return {
            "advisories": advisories,
            "iocs": iocs,
            "assets": assets,
            "revoked": revoked,
            "advisories_par_niveau": {label_name(row[0]): row[1] for row in by_level},
        }


def _validate_common(item: dict[str, Any]) -> int:
    level = parse_level(item.get("classification"))
    item["classification"] = level
    item["compartments"] = [normalize_compartment(value) for value in item.get("compartments", [])]
    return level


def init_db(
    db_path: Path | str = DB_PATH,
    data_dir: Path | str = DATA_DIR,
    force: bool = False,
) -> dict[str, Any]:
    db_path = Path(db_path)
    data_dir = Path(data_dir)
    if db_path.exists():
        if not force:
            return Store(db_path, read_only=True).stats()
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        adv_path = data_dir / "advisories.jsonl"
        ioc_path = data_dir / "iocs.jsonl"
        asset_path = data_dir / "assets.json"
        advisories: list[dict[str, Any]] = []
        for line in adv_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                advisories.append(json.loads(line))
        iocs: list[dict[str, Any]] = []
        for line in ioc_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                iocs.append(json.loads(line))
        assets = json.loads(asset_path.read_text(encoding="utf-8"))

        for item in advisories:
            _validate_common(item)
            title = sanitize.neutralize(item["title"])
            summary = sanitize.neutralize(item["summary"])
            body = sanitize.neutralize(item["body"])
            flags = sorted(set(title.flags + summary.flags + body.flags))
            parse_ts(item["published_at"])
            cvss = float(item["cvss"])
            epss = float(item["epss"])
            trust = float(item["source_trust"])
            if not (0 <= cvss <= 10 and 0 <= epss <= 1 and 0 <= trust <= 1):
                raise StoreError(f"plage numérique invalide pour {item['id']}")
            conn.execute(
                "INSERT INTO advisories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item["id"], title.text, summary.text, body.text, item["classification"],
                    _json_table(item["compartments"]), item["source"], trust, item["published_at"],
                    cvss, epss, int(bool(item["kev"])), _json_table(item.get("products", [])),
                    item.get("source_identity"), item.get("canary"), _json_table(flags),
                    hashlib.sha256(item["body"].encode("utf-8")).hexdigest(), item.get("advisory_type", "bulletin"),
                ),
            )
        for item in iocs:
            _validate_common(item)
            sanitize.validate_ioc_value(item["value"], item["type"])
            parse_ts(item["first_seen"])
            conf = float(item["confidence"])
            if not 0 <= conf <= 1:
                raise StoreError(f"confiance invalide pour {item['id']}")
            conn.execute(
                "INSERT INTO iocs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item["id"], item["type"], item["value"], item["family"], _json_table(item.get("tags", [])),
                    conf, item["first_seen"], item["classification"], _json_table(item["compartments"]),
                    item["source"], _json_table(item.get("advisory_ids", [])),
                ),
            )
        for item in assets:
            _validate_common(item)
            crit = int(item["criticality"])
            expo = int(item["exposure"])
            if not (1 <= crit <= 5 and 1 <= expo <= 5):
                raise StoreError(f"criticité/exposition invalide pour {item['id']}")
            conn.execute(
                "INSERT INTO assets VALUES (?,?,?,?,?,?,?,?)",
                (
                    item["id"], item["name"], crit, expo, item["classification"],
                    _json_table(item["compartments"]), _json_table(item.get("products", [])), item["owner"],
                ),
            )
        conn.commit()
    finally:
        conn.close()
    os.chmod(db_path, 0o640)
    return Store(db_path, read_only=True).stats()
