"""Console d'exploitation du serveur TEK-UP Threat Intelligence."""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ti_server import auth  # noqa: E402
from ti_server.audit import AuditLog  # noqa: E402
from ti_server.config import (  # noqa: E402
    AUDIT_PATH,
    DB_PATH,
    KEY_PATH,
    LEVELS,
    ROLES,
    PURPOSES,
    iso,
    label_name,
    tlp_name,
    utcnow,
)
from ti_server.store import Store, init_db  # noqa: E402


def _posture(kind: str) -> dict:
    now = iso(utcnow())
    if kind == "conforme":
        return {
            "posture": "conforme", "edr": True, "disk_encryption": True,
            "os_supported": True, "attested_at": now, "agent": "poste-lab-01",
        }
    return {
        "posture": "non-conforme", "edr": False, "disk_encryption": True,
        "os_supported": True, "attested_at": now, "agent": "poste-hors-norme",
    }


def _issue(args: argparse.Namespace, secret: bytes, overrides: dict | None = None) -> tuple[str, dict]:
    claims = {
        "sub": args.sub,
        "role": args.role,
        "clearance": args.clearance,
        "compartments": [item.strip().upper() for item in (args.compartments or "").split(",") if item.strip()],
        "purpose": args.purpose,
        "endpoint": _posture(args.posture),
        "issuer": "tekup-ti-admin",
        "scope": "mcp:read",
    }
    if overrides:
        claims.update(overrides)
    ttl = -3600 if args.expired else args.ttl
    token, payload = auth.issue_token(secret, claims, ttl_seconds=ttl)
    return token, payload


def cmd_init_db(args: argparse.Namespace) -> int:
    stats = init_db(DB_PATH, force=args.force)
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


def cmd_issue_token(args: argparse.Namespace) -> int:
    secret = auth.ensure_key(KEY_PATH)
    token, payload = _issue(args, secret)
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token + "\n", encoding="utf-8")
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    if args.meta:
        meta = dict(payload)
        meta.pop("jti", None) if args.hide_jti else None
        Path(args.meta).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(args.meta, stat.S_IRUSR | stat.S_IWUSR)
    print(token)
    summary = {
        "subject": payload["sub"], "role": payload["role"],
        "clearance": label_name(payload["clearance"]), "compartments": payload["compartments"],
        "purpose": payload["purpose"], "jti": payload["jti"],
        "expire_le": iso(__import__("datetime").datetime.fromtimestamp(payload["exp"], tz=__import__("datetime").timezone.utc)),
        "posture": payload["endpoint"]["posture"],
    }
    sys.stderr.write(json.dumps(summary, ensure_ascii=False) + "\n")
    return 0


def cmd_inspect_token(args: argparse.Namespace) -> int:
    token = args.token
    if args.file:
        token = Path(args.file).read_text(encoding="utf-8").strip()
    claims = auth.describe_token(token)
    if "clearance" in claims:
        claims["clearance_name"] = label_name(claims["clearance"])
        claims["tlp"] = tlp_name(claims["clearance"])
    print(json.dumps(claims, ensure_ascii=False, indent=2))
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    store = Store(DB_PATH, read_only=False)
    store.revoke(args.jti, args.reason)
    print(json.dumps({"revoked": args.jti, "at": iso(utcnow()), "reason": args.reason},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_verify_audit(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else AUDIT_PATH
    result = AuditLog(path).verify()
    print(json.dumps({"fichier": str(path), **result.as_dict()}, ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


def cmd_tail_audit(args: argparse.Namespace) -> int:
    path = Path(args.path) if args.path else AUDIT_PATH
    entries = AuditLog(path).tail(args.limit)
    for entry in entries:
        print(json.dumps(entry, ensure_ascii=False))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    print(json.dumps(Store(DB_PATH, read_only=True).stats(), ensure_ascii=False, indent=2))
    return 0


def cmd_demo_tokens(args: argparse.Namespace) -> int:
    directory = Path(args.dir)
    directory.mkdir(parents=True, exist_ok=True)
    secret = auth.ensure_key(KEY_PATH)
    profiles = [
        ("analyst_cti", "agent-soc-01", "analyst", 2, "CTI", "triage", "conforme", False),
        ("crypto_lead", "agent-crypto-02", "lead", 3, "CTI,CRYPTO,ATTRIB", "investigation", "conforme", False),
        ("reader_low", "agent-stage-03", "reader", 1, "", "reporting", "conforme", False),
        ("wrong_comp", "agent-attrib-04", "analyst", 3, "CTI", "investigation", "conforme", False),
        ("noncompliant", "agent-byod-05", "analyst", 3, "CTI,CRYPTO,ATTRIB", "triage", "non-conforme", False),
        ("rate_probe", "agent-load-06", "analyst", 2, "CTI", "triage", "conforme", False),
        ("revoked_probe", "agent-revoke-07", "analyst", 2, "CTI", "triage", "conforme", False),
        ("expired_probe", "agent-old-08", "analyst", 3, "CTI,CRYPTO,ATTRIB", "triage", "conforme", True),
        ("auditor", "agent-audit-09", "auditor", 2, "CTI,INC-2026-014", "audit", "conforme", False),
    ]
    manifest = []
    env_lines = []
    for name, sub, role, clearance, comps, purpose, posture, expired in profiles:
        args_ns = argparse.Namespace(sub=sub, role=role, clearance=clearance,
                                     compartments=comps, purpose=purpose, posture=posture,
                                     expired=expired, ttl=8 * 3600)
        token, payload = _issue(args_ns, secret)
        path = directory / f"{name}.tok"
        path.write_text(token + "\n", encoding="utf-8")
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        env_lines.append(f"export TI_TOKEN_{name.upper()}={token}")
        manifest.append({
            "nom": name, "fichier": str(path), "sub": sub, "role": role,
            "clearance": clearance, "clearance_name": label_name(clearance),
            "compartments": payload["compartments"], "purpose": purpose,
            "posture": posture, "jti": payload["jti"],
            "exp": payload["exp"], "expire": expired,
        })
    (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    env_path = directory / "tokens.env"
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
    print(json.dumps({"profils": manifest, "repertoire": str(directory)}, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exploitation du serveur MCP Threat Intelligence TEK-UP")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init-db", help="Construire la base à partir des flux synthétiques")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_init_db)

    p = sub.add_parser("issue-token", help="Émettre un jeton de capacité signé")
    p.add_argument("--sub", required=True)
    p.add_argument("--role", choices=ROLES, default="analyst")
    p.add_argument("--clearance", type=int, choices=sorted(LEVELS), default=1)
    p.add_argument("--compartments", default="")
    p.add_argument("--purpose", choices=PURPOSES, default="triage")
    p.add_argument("--posture", choices=["conforme", "non-conforme"], default="conforme")
    p.add_argument("--ttl", type=int, default=8 * 3600)
    p.add_argument("--expired", action="store_true")
    p.add_argument("--out")
    p.add_argument("--meta")
    p.add_argument("--hide-jti", action="store_true")
    p.set_defaults(func=cmd_issue_token)

    p = sub.add_parser("inspect-token", help="Afficher les revendications d'un jeton")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--token")
    group.add_argument("--file")
    p.set_defaults(func=cmd_inspect_token)

    p = sub.add_parser("revoke", help="Révoquer un jeton par son identifiant jti")
    p.add_argument("--jti", required=True)
    p.add_argument("--reason", default="révocation manuelle")
    p.set_defaults(func=cmd_revoke)

    p = sub.add_parser("verify-audit", help="Vérifier la chaîne d'audit")
    p.add_argument("--path")
    p.set_defaults(func=cmd_verify_audit)

    p = sub.add_parser("tail-audit", help="Afficher les dernières entrées d'audit")
    p.add_argument("--path")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_tail_audit)

    p = sub.add_parser("stats", help="Statistiques de la base")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("demo-tokens", help="Générer les profils de démonstration")
    p.add_argument("--dir", default=str(PROJECT / "preuves" / "tokens"))
    p.set_defaults(func=cmd_demo_tokens)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
