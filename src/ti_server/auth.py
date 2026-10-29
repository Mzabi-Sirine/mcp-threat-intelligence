"""Jetons de capacité signés (HMAC-SHA256), sans dépendance externe."""
from __future__ import annotations

import base64
import datetime as dt
import hmac
import json
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import utcnow

PREFIX = "ti1"


class TokenError(ValueError):
    def __init__(self, code: str, message: str = "jeton invalide"):
        super().__init__(message)
        self.code = code


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def unb64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def ensure_key(path: Path | str) -> bytes:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = path.read_bytes()
        if len(data) < 32:
            raise TokenError("CLE_INVALIDE", "clé trop courte")
        return data
    key = secrets.token_bytes(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(key)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return key


def issue_token(secret: bytes, claims: dict[str, Any], ttl_seconds: int = 8 * 3600) -> tuple[str, dict[str, Any]]:
    now = utcnow()
    payload = dict(claims)
    payload.setdefault("jti", secrets.token_hex(12))
    payload["iat"] = int(now.timestamp())
    payload["exp"] = int(now.timestamp()) + int(ttl_seconds)
    body = b64url(canonical_json(payload))
    signature = hmac.new(secret, f"{PREFIX}.{body}".encode("ascii"), "sha256").digest()
    return f"{PREFIX}.{body}.{b64url(signature)}", payload


@dataclass
class VerifiedToken:
    claims: dict[str, Any]
    signed_at: Any
    expires_at: Any


def verify_token(token: str, secret: bytes, check_time: bool = True) -> VerifiedToken:
    if not isinstance(token, str) or token.count(".") != 2:
        raise TokenError("TOKEN_INVALIDE", "format de jeton invalide")
    prefix, body, signature = token.split(".")
    if prefix != PREFIX:
        raise TokenError("TOKEN_INVALIDE", "préfixe de jeton invalide")
    expected = hmac.new(secret, f"{PREFIX}.{body}".encode("ascii"), "sha256").digest()
    try:
        received = unb64url(signature)
    except Exception as exc:
        raise TokenError("TOKEN_INVALIDE", "signature illisible") from exc
    if not hmac.compare_digest(expected, received):
        raise TokenError("SIGNATURE_INVALIDE", "signature incorrecte")
    try:
        claims = json.loads(unb64url(body))
    except Exception as exc:
        raise TokenError("TOKEN_INVALIDE", "charge utile illisible") from exc
    if not isinstance(claims, dict):
        raise TokenError("TOKEN_INVALIDE", "charge utile invalide")
    for required in ("sub", "role", "clearance", "compartments", "purpose", "endpoint", "jti", "iat", "exp"):
        if required not in claims:
            raise TokenError("TOKEN_INVALIDE", f"revendication manquante: {required}")
    if isinstance(claims["clearance"], bool) or not isinstance(claims["clearance"], int) or claims["clearance"] not in (0, 1, 2, 3):
        raise TokenError("TOKEN_INVALIDE", "habilitation invalide")
    if not isinstance(claims["compartments"], list) or not isinstance(claims["endpoint"], dict):
        raise TokenError("TOKEN_INVALIDE", "structure du jeton invalide")
    try:
        expires_at = dt.datetime.fromtimestamp(int(claims["exp"]), tz=dt.timezone.utc)
        signed_at = dt.datetime.fromtimestamp(int(claims["iat"]), tz=dt.timezone.utc)
    except Exception as exc:
        raise TokenError("TOKEN_INVALIDE", "horodatages invalides") from exc
    if check_time:
        now = utcnow()
        if expires_at <= now:
            raise TokenError("TOKEN_EXPIRE", "jeton expiré")
        if signed_at.timestamp() > now.timestamp() + 120:
            raise TokenError("TOKEN_INVALIDE", "jeton émis dans le futur")
    return VerifiedToken(claims=claims, signed_at=signed_at, expires_at=expires_at)


def describe_token(token: str) -> dict[str, Any]:
    """Lecture non authentifiée, réservée à l'affichage de démonstration."""
    parts = token.split(".")
    if len(parts) != 3:
        return {"erreur": "format invalide"}
    try:
        return json.loads(unb64url(parts[1]))
    except Exception:
        return {"erreur": "charge utile illisible"}
