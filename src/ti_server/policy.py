"""Moteur de décision ABAC : jeton, posture, habilitation, cloisonnement."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any

from .auth import TokenError, verify_token
from .config import (
    ENDPOINT_MAX_AGE_S,
    PURPOSES,
    ROLES,
    TOOL_PURPOSES,
    TOOL_ROLES,
    label_name,
    parse_ts,
    tlp_name,
    utcnow,
)
from .labels import clearance_covers, compartments_cover, max_level

GENERIC_DENIAL = "La demande ne peut pas être satisfaite avec les droits présentés."


@dataclass
class Decision:
    allowed: bool
    code: str
    detail: str
    claims: dict[str, Any] | None = None

    def public_error(self, request_id: str) -> dict[str, Any]:
        return {
            "erreur": self.code,
            "message": GENERIC_DENIAL,
            "request_id": request_id,
        }


def _as_bool(value: Any) -> bool:
    return value is True


def check_endpoint(claims: dict[str, Any], now: dt.datetime) -> Decision:
    endpoint = claims.get("endpoint")
    if not isinstance(endpoint, dict):
        return Decision(False, "POSTURE_NON_CONFORME", "bloc de posture absent")
    if endpoint.get("posture") != "conforme":
        return Decision(False, "POSTURE_NON_CONFORME", "poste déclaré non conforme")
    if not _as_bool(endpoint.get("edr")):
        return Decision(False, "POSTURE_NON_CONFORME", "protection EDR absente")
    if not _as_bool(endpoint.get("disk_encryption")):
        return Decision(False, "POSTURE_NON_CONFORME", "chiffrement de disque absent")
    if not _as_bool(endpoint.get("os_supported")):
        return Decision(False, "POSTURE_NON_CONFORME", "système non supporté")
    try:
        attested = parse_ts(endpoint.get("attested_at", ""))
    except Exception:
        return Decision(False, "POSTURE_NON_CONFORME", "attestation absente ou illisible")
    age = (now - attested).total_seconds()
    if age > ENDPOINT_MAX_AGE_S:
        return Decision(False, "POSTURE_NON_CONFORME", f"attestation trop ancienne ({int(age)} s)")
    if age < -300:
        return Decision(False, "POSTURE_NON_CONFORME", "attestation datée dans le futur")
    return Decision(True, "OK", "posture conforme")


def authenticate(token: str, secret: bytes, store: Any, now: dt.datetime | None = None) -> Decision:
    now = now or utcnow()
    try:
        verified = verify_token(token, secret)
    except TokenError as exc:
        return Decision(False, exc.code, str(exc))
    claims = verified.claims
    if store.is_revoked(claims["jti"]):
        return Decision(False, "TOKEN_REVOQUE", "jeton révoqué")
    if claims.get("role") not in ROLES:
        return Decision(False, "TOKEN_INVALIDE", "rôle inconnu")
    if claims.get("purpose") not in PURPOSES:
        return Decision(False, "TOKEN_INVALIDE", "finalité inconnue")
    endpoint = check_endpoint(claims, now)
    if not endpoint.allowed:
        return Decision(False, endpoint.code, endpoint.detail, claims)
    return Decision(True, "OK", "jeton valide", claims)


def authorize_tool(claims: dict[str, Any], tool_name: str) -> Decision:
    if tool_name not in TOOL_PURPOSES:
        return Decision(False, "OUTIL_NON_AUTORISE", f"outil inconnu: {tool_name}", claims)
    if claims.get("purpose") not in TOOL_PURPOSES[tool_name]:
        return Decision(False, "OUTIL_NON_AUTORISE", "finalité incompatible avec l'outil", claims)
    if claims.get("role") not in TOOL_ROLES[tool_name]:
        return Decision(False, "PRIVILEGE_INSUFFISANT", "rôle incompatible avec l'outil", claims)
    return Decision(True, "OK", "outil autorisé", claims)


def can_read(claims: dict[str, Any], item: dict[str, Any]) -> Decision:
    level = int(item.get("classification", 3))
    if not clearance_covers(int(claims.get("clearance", 0)), level):
        return Decision(False, "HABILITATION_INSUFFISANTE", f"habilitation < {label_name(level)}", claims)
    if not compartments_cover(claims.get("compartments", []), item.get("compartments", [])):
        return Decision(False, "BESOIN_CONNAITRE_NON_SATISFAIT", "cloisonnement non satisfait", claims)
    return Decision(True, "OK", "accès autorisé", claims)


def filter_readable(claims: dict[str, Any], items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if can_read(claims, item).allowed]


def redact(claims: dict[str, Any], item: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    """Retire les champs dont le niveau dépasse l'habilitation. Retourne aussi les avertissements."""
    result = dict(item)
    redacted: list[str] = []
    caveats: list[str] = []
    if result.get("source_identity") is not None and int(claims.get("clearance", 0)) < 3:
        result["source_identity"] = None
        redacted.append("source_identity")
        caveats.append("Identité de la source masquée (champ Secret).")
    if result.get("canary") is not None and int(claims.get("clearance", 0)) < 3:
        result["canary"] = None
        redacted.append("canary")
        caveats.append("Jeton leurre masqué.")
    result.pop("original_sha256", None)
    return result, redacted, caveats


def response_label(claims: dict[str, Any], items: list[dict[str, Any]]) -> tuple[int, str, str]:
    levels = [int(item.get("classification", 0)) for item in items]
    level = max_level(levels, default=min(int(claims.get("clearance", 0)), 1))
    return level, label_name(level), tlp_name(level)
