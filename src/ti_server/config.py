"""Configuration centrale et constantes du serveur MCP Threat Intelligence."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

VERSION = "1.0.0"
SCHEMA_VERSION = "2025-06-18"

ROOT = Path(os.environ.get("TI_HOME", Path(__file__).resolve().parents[2]))
DATA_DIR = Path(os.environ.get("TI_DATA", ROOT / "data"))
PREUVES_DIR = Path(os.environ.get("TI_PREUVES", ROOT / "preuves"))
DB_PATH = Path(os.environ.get("TI_DB", DATA_DIR / "ti.db"))
KEY_PATH = Path(os.environ.get("TI_KEY_PATH", DATA_DIR / "keys" / "token.key"))
AUDIT_PATH = Path(os.environ.get("TI_AUDIT", PREUVES_DIR / "logs" / "audit.jsonl"))
AUDIT_KEY_PATH = Path(os.environ.get("TI_AUDIT_KEY", DATA_DIR / "keys" / "audit.key"))

LEVELS = {0: "Public", 1: "Interne", 2: "Confidentiel", 3: "Secret"}
TLP = {0: "TLP:CLEAR", 1: "TLP:GREEN", 2: "TLP:AMBER", 3: "TLP:RED"}
LEVEL_BY_NAME = {v.lower(): k for k, v in LEVELS.items()}
TLP_BY_NAME = {v.lower(): k for k, v in TLP.items()}

ROLES = ("analyst", "responder", "lead", "reader", "auditor")
PURPOSES = ("triage", "investigation", "reporting", "audit")

TOOL_PURPOSES = {
    "ti_search": {"triage", "investigation", "reporting", "audit"},
    "ti_get_advisory": {"triage", "investigation", "reporting", "audit"},
    "ti_enrich_ioc": {"triage", "investigation", "reporting", "audit"},
    "ti_correlate": {"triage", "investigation", "reporting", "audit"},
    "ti_score_asset": {"triage", "investigation"},
    "ti_health": {"triage", "investigation", "reporting", "audit"},
}

TOOL_ROLES = {
    "ti_search": {"analyst", "responder", "lead", "reader", "auditor"},
    "ti_get_advisory": {"analyst", "responder", "lead", "reader", "auditor"},
    "ti_enrich_ioc": {"analyst", "responder", "lead", "reader", "auditor"},
    "ti_correlate": {"analyst", "responder", "lead", "reader", "auditor"},
    "ti_score_asset": {"analyst", "responder", "lead"},
    "ti_health": {"analyst", "responder", "lead", "reader", "auditor"},
}

MAX_QUERY_LEN = 200
MAX_LINE_BYTES = 1_048_576
MAX_JSON_DEPTH = 8
ENDPOINT_MAX_AGE_S = 24 * 3600
RATE_LIMIT = int(os.environ.get("TI_RATE_LIMIT", "120"))
RATE_WINDOW_S = int(os.environ.get("TI_RATE_WINDOW", "60"))
CONFIDENCE_HALF_LIFE_DAYS = 30.0
FIXED_NOW = os.environ.get("TI_NOW")


class ConfigError(RuntimeError):
    pass


def utcnow() -> dt.datetime:
    if FIXED_NOW:
        try:
            value = FIXED_NOW.replace("Z", "+00:00")
            parsed = dt.datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc)
        except ValueError as exc:  # pragma: no cover - configuration invalide
            raise ConfigError(f"TI_NOW invalide: {FIXED_NOW}") from exc
    return dt.datetime.now(dt.timezone.utc)


def iso(value: dt.datetime | None = None) -> str:
    value = value or utcnow()
    return value.astimezone(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_ts(value: str) -> dt.datetime:
    if not isinstance(value, str):
        raise ValueError("horodatage attendu")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def label_name(level: int) -> str:
    return LEVELS.get(int(level), "Secret")


def tlp_name(level: int) -> str:
    return TLP.get(int(level), "TLP:RED")
