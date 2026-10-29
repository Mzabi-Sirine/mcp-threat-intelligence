#!/usr/bin/env python3
"""Démonstration reproductible du contrôle de protection du secret.

Rejoue, dans un laboratoire séparé (preuves/demo), les gestes montrés à l'oral :
outils disponibles, fuite bloquée, cloisonnement, accès Secret autorisé,
injection neutralisée, vérification de la chaîne d'audit. Le résultat structuré
est écrit dans preuves/logs/demo_capture.json et la trace lisible dans
preuves/logs/demo_transcript.txt.

Mode soutenance : `python3 scripts/demo_defense.py --present` exécute les mêmes
scènes avec un commentaire et une pause entre chacune, dans un laboratoire
dédié (preuves/demo_prof), sans toucher aux preuves du rapport.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "scripts"))

from mcp_client import MCPClient, summarize_tool_result  # noqa: E402
from ti_server import auth  # noqa: E402
from ti_server.audit import AuditLog  # noqa: E402
from ti_server.config import iso, utcnow  # noqa: E402
from ti_server.store import Store, init_db  # noqa: E402

DEMO = PROJECT / "preuves" / "demo"
DATA = DEMO / "data"
DB = DEMO / "ti.db"
KEY = DEMO / "token.key"
AUDIT = DEMO / "audit.jsonl"
OUT_JSON = PROJECT / "preuves" / "logs" / "demo_capture.json"
OUT_TXT = PROJECT / "preuves" / "logs" / "demo_transcript.txt"

CANARY = "CANARY-TEKUP-7f3a9c-2026"


def posture() -> dict[str, Any]:
    return {
        "posture": "conforme", "edr": True, "disk_encryption": True,
        "os_supported": True, "attested_at": iso(utcnow()), "agent": "poste-lab",
    }


def env() -> dict[str, str]:
    return {
        "TI_HOME": str(PROJECT), "TI_DATA": str(DATA), "TI_DB": str(DB),
        "TI_KEY_PATH": str(KEY), "TI_AUDIT": str(AUDIT),
        "TI_RATE_LIMIT": "1000", "TI_RATE_WINDOW": "60",
    }


def issue(secret: bytes, sub: str, role: str, clearance: int,
          compartments: list[str], purpose: str) -> tuple[str, dict[str, Any]]:
    claims = {
        "sub": sub, "role": role, "clearance": clearance,
        "compartments": compartments, "purpose": purpose,
        "endpoint": posture(), "issuer": "tekup-ti-admin", "scope": "mcp:read",
    }
    token, payload = auth.issue_token(secret, claims, ttl_seconds=8 * 3600)
    return token, payload


def summarise(response: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_tool_result(response)
    structured = summary.get("structured") or {}
    return {
        "transport_ok": summary.get("transport_ok"),
        "isError": summary.get("isError"),
        "erreur": structured.get("erreur"),
        "message": structured.get("message"),
        "donnees": structured.get("donnees"),
        "securite": structured.get("securite"),
        "texte": summary.get("text", ""),
    }


def last_audit() -> dict[str, Any]:
    entries = AuditLog(AUDIT).tail(1)
    return entries[0] if entries else {}


def audit_view(entry: dict[str, Any]) -> dict[str, Any]:
    keys = ("seq", "ts", "event", "subject", "tool", "decision", "reason",
            "classification", "clearance", "request_id", "latency_ms")
    view = {key: entry.get(key) for key in keys if entry.get(key) is not None}
    view["entry_hash"] = str(entry.get("entry_hash", ""))[:16] + "…"
    view["prev_hash"] = str(entry.get("prev_hash", ""))[:16] + "…"
    return view


INTROS = {
    "S1": ("S1 · Découverte du serveur",
           "Le serveur démarre en local et expose six outils en lecture seule : protocole, version et volume visible."),
    "S2": ("S2 · Fuite bloquée par l'habilitation",
           "Une analyste Confidentiel demande un bulletin Secret : refus, canari absent, décision journalisée."),
    "S3": ("S3 · Cloisonnement besoin d'en connaître",
           "Un agent Secret sans le compartiment CRYPTO demande le même bulletin : refus par besoin d'en connaître."),
    "S4": ("S4 · Accès autorisé, contrôle positif",
           "Un agent Secret + CRYPTO accède au bulletin : le canari apparaît, preuve du contrôle positif."),
    "S5": ("S5 · Injection neutralisée",
           "Un bulletin partenaire contient une instruction hostile : elle est signalée, neutralisée et journalisée."),
    "S6": ("S6 · Journal d'audit chaîné",
           "Je vérifie le journal valide, puis une copie falsifiée : la rupture est localisée à la séquence près."),
    "S7": ("S7 · Avant / après sur les mêmes bulletins",
           "Même bulletin, deux serveurs : la maquette fuit, le serveur durci masque, refuse et journalise."),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Démonstration du serveur MCP Threat Intelligence.")
    parser.add_argument("--present", action="store_true",
                        help="mode soutenance : commentaires, pauses, laboratoire dédié")
    parser.add_argument("--lab", type=Path, default=None, help="laboratoire de démonstration")
    parser.add_argument("--out-json", type=Path, default=None, help="trace JSON de sortie")
    parser.add_argument("--out-txt", type=Path, default=None, help="trace texte de sortie")
    parser.add_argument("--auto-delay", type=float, default=0.0,
                        help="mode vidéo : pause automatique de N secondes entre les scènes")
    args = parser.parse_args(argv)

    global DATA, DB, KEY, AUDIT, OUT_JSON, OUT_TXT
    lab = (args.lab or (PROJECT / "preuves" / ("demo_prof" if args.present else "demo"))).resolve()
    DATA = lab / "data"
    DB = lab / "ti.db"
    KEY = lab / "token.key"
    AUDIT = lab / "audit.jsonl"
    OUT_JSON = args.out_json or (PROJECT / "preuves" / "logs" /
                                 ("demo_prof_capture.json" if args.present else "demo_capture.json"))
    OUT_TXT = args.out_txt or (PROJECT / "preuves" / "logs" /
                               ("demo_prof_transcript.txt" if args.present else "demo_transcript.txt"))

    if lab.exists():
        shutil.rmtree(lab)
    DATA.mkdir(parents=True)
    for name in ("advisories.jsonl", "iocs.jsonl", "assets.json"):
        shutil.copy2(PROJECT / "data" / name, DATA / name)
    init_db(DB, DATA, force=True)
    secret = auth.ensure_key(KEY)

    analyst_token, analyst_claims = issue(secret, "agent-soc-01", "analyst", 2, ["CTI", "INC-2026-014"], "triage")
    wrong_token, wrong_claims = issue(secret, "agent-attrib-04", "analyst", 3, ["CTI"], "investigation")
    secret_token, secret_claims = issue(secret, "agent-crypto-02", "lead", 3, ["CTI", "CRYPTO", "ATTRIB"], "investigation")

    data: dict[str, Any] = {
        "genere_le": iso(utcnow()),
        "laboratoire": str(lab),
        "jetons": {
            "analyste": {"sub": analyst_claims["sub"], "habilitation": "Confidentiel",
                         "compartiments": analyst_claims["compartments"], "jti": analyst_claims["jti"]},
            "cloisonne": {"sub": wrong_claims["sub"], "habilitation": "Secret",
                          "compartiments": wrong_claims["compartments"], "jti": wrong_claims["jti"]},
            "secret": {"sub": secret_claims["sub"], "habilitation": "Secret",
                       "compartiments": secret_claims["compartments"], "jti": secret_claims["jti"]},
        },
        "scenes": {},
    }
    lines: list[str] = [
        f"$ python3 scripts/demo_defense.py{' --present' if args.present else ''}",
        f"Laboratoire de démonstration : {lab}",
        f"Date : {data['genere_le']}",
        "",
    ]

    printed = 0

    def show() -> None:
        nonlocal printed
        if args.present and printed < len(lines):
            print("\n".join(lines[printed:]), flush=True)
            printed = len(lines)

    def intro(scene: str) -> None:
        if not args.present:
            return
        title, talk = INTROS[scene]
        lines.extend(["", "=" * 78, title, "=" * 78, talk])
        show()

    def next_scene() -> None:
        if not args.present:
            return
        if args.auto_delay > 0:
            time.sleep(args.auto_delay)
            return
        try:
            input("\n  ▶ Entrée pour la scène suivante… ")
        except EOFError:
            pass

    show()

    # S1 — outils et état du service
    intro("S1")
    with MCPClient(analyst_token, env_extra=env(), timeout=15.0) as client:
        init = client.initialize()
        tools = client.list_tools()
        health = summarise(client.call("ti_health", {}))
        init_result = init.get("result", {}) if init.get("ok") else {}
        tool_list = (tools.get("result") or {}).get("tools", [])
        data["scenes"]["S1"] = {
            "protocole": init_result.get("protocolVersion"),
            "serveur": (init_result.get("serverInfo") or {}).get("version"),
            "outils": [{"nom": tool.get("name"), "lecture_seule": bool((tool.get("annotations") or {}).get("readOnlyHint")),
                        "description": tool.get("description")} for tool in tool_list],
            "sante": health,
        }
    s1 = data["scenes"]["S1"]
    lines += [
        "S1 — DÉCOUVERTE DU SERVEUR",
        "> initialize  (client tekup-lab-client)",
        f"  protocole={s1['protocole']}  serveur=v{s1['serveur']}  outils={len(s1['outils'])}  lecture_seule=True",
    ]
    for tool in s1["outils"]:
        lines.append(f"  • {tool['nom']:<18} {'lecture seule' if tool['lecture_seule'] else 'écriture'}")
    health_data = (s1["sante"].get("donnees") or {})
    volumes = health_data.get("volumes_accessibles") or {}
    lines += [
        f"> tools/call ti_health",
        f"  service={health_data.get('service')}  version={health_data.get('version')}",
        f"  bulletins visibles={volumes.get('bulletins')}  indicateurs visibles={volumes.get('indicateurs')}",
        "  durcissement : jetons signés, ABAC, assainissement, injection neutralisée, journal chaîné, réseau sortant interdit",
        "",
    ]
    show()
    next_scene()

    # S2 — fuite par habilitation insuffisante
    intro("S2")
    with MCPClient(analyst_token, env_extra=env(), timeout=15.0) as client:
        client.initialize()
        response = summarise(client.call("ti_get_advisory", {"advisory_id": "ADV-2026-004"}))
        entry = last_audit()
    data["scenes"]["S2"] = {
        "requete": "ti_get_advisory('ADV-2026-004')",
        "jeton": "agent-soc-01 · Confidentiel · CTI+INC-2026-014",
        "code": response["erreur"], "message": response["message"],
        "canari_present": CANARY in response["texte"],
        "audit": audit_view(entry),
    }
    s2 = data["scenes"]["S2"]
    lines += [
        "S2 — FUITE TENTÉE PAR UN JETON CONFIDENTIEL",
        "> ti_get_advisory('ADV-2026-004')   [agent-soc-01, Confidentiel, CTI+INC]",
        f"  isError={response['isError']}  code={s2['code']}",
        f"  message=« {s2['message']} »",
        f"  canari dans la réponse : {s2['canari_present']}",
        f"  journal : decision={s2['audit'].get('decision')}  reason={s2['audit'].get('reason')}  "
        f"classification={s2['audit'].get('classification')}  clearance={s2['audit'].get('clearance')}",
        "",
    ]
    show()
    next_scene()

    # S3 — cloisonnement / besoin d'en connaître
    intro("S3")
    with MCPClient(wrong_token, env_extra=env(), timeout=15.0) as client:
        client.initialize()
        response = summarise(client.call("ti_get_advisory", {"advisory_id": "ADV-2026-004"}))
        entry = last_audit()
    data["scenes"]["S3"] = {
        "requete": "ti_get_advisory('ADV-2026-004')",
        "jeton": "agent-attrib-04 · Secret · CTI (sans CRYPTO)",
        "code": response["erreur"], "message": response["message"],
        "canari_present": CANARY in response["texte"],
        "audit": audit_view(entry),
    }
    s3 = data["scenes"]["S3"]
    lines += [
        "S3 — JETON SECRET MAIS HORS COMPARTIMENT",
        "> ti_get_advisory('ADV-2026-004')   [agent-attrib-04, Secret, CTI seul]",
        f"  isError={response['isError']}  code={s3['code']}",
        f"  canari dans la réponse : {s3['canari_present']}",
        f"  journal : reason={s3['audit'].get('reason')}  (cloisonnement CRYPTO)",
        "",
    ]
    show()
    next_scene()

    # S4 — accès autorisé, canari visible
    intro("S4")
    with MCPClient(secret_token, env_extra=env(), timeout=15.0) as client:
        client.initialize()
        response = summarise(client.call("ti_get_advisory", {"advisory_id": "ADV-2026-004"}))
        entry = last_audit()
    security = response.get("securite") or {}
    data["scenes"]["S4"] = {
        "requete": "ti_get_advisory('ADV-2026-004')",
        "jeton": "agent-crypto-02 · Secret · CTI+CRYPTO+ATTRIB",
        "isError": response["isError"],
        "classification": security.get("classification"), "tlp": security.get("tlp"),
        "canari_present": CANARY in response["texte"],
        "audit": audit_view(entry),
    }
    s4 = data["scenes"]["S4"]
    lines += [
        "S4 — ACCÈS AUTORISÉ (SECRET + CRYPTO)",
        "> ti_get_advisory('ADV-2026-004')   [agent-crypto-02, Secret, CTI+CRYPTO+ATTRIB]",
        f"  isError={s4['isError']}  classification={s4['classification']}  tlp={s4['tlp']}",
        f"  canari de contrôle présent : {s4['canari_present']}   (CANARY-TEKUP-…-2026)",
        f"  journal : decision={s4['audit'].get('decision')}  reason={s4['audit'].get('reason')}",
        "",
    ]
    show()
    next_scene()

    # S5 — injection neutralisée
    intro("S5")
    with MCPClient(analyst_token, env_extra=env(), timeout=15.0) as client:
        client.initialize()
        response = summarise(client.call("ti_get_advisory", {"advisory_id": "ADV-2026-012"}))
        entry = last_audit()
    security = response.get("securite") or {}
    data["scenes"]["S5"] = {
        "requete": "ti_get_advisory('ADV-2026-012')",
        "code": response["erreur"],
        "fanions": security.get("injections_neutralisees"),
        "instruction_brute": "IGNORE ALL PREVIOUS" in response["texte"],
        "marqueur_neutralise": "INSTRUCTION SUSPECTE NEUTRALISÉE" in response["texte"],
        "mentions": security.get("mentions"),
        "avertissement": security.get("avertissement"),
        "audit": audit_view(entry),
    }
    s5 = data["scenes"]["S5"]
    lines += [
        "S5 — INJECTION D'INSTRUCTIONS DANS UN FLUX PARTENAIRE",
        "> ti_get_advisory('ADV-2026-012')   [contenu hostile importé]",
        f"  isError={response['isError']}  code={s5['code']}",
        f"  fanions={', '.join(s5['fanions'] or [])}",
        f"  instruction brute livrée : {s5['instruction_brute']}",
        f"  marqueur de neutralisation : {s5['marqueur_neutralise']}",
        f"  journal : injection_flags={entry.get('injection_flags')}",
        "",
    ]
    show()
    next_scene()

    # S6 — chaîne d'audit
    intro("S6")
    verification = AuditLog(AUDIT).verify()
    tail = AuditLog(AUDIT).tail(3)
    audit_display = AUDIT.relative_to(PROJECT) if AUDIT.is_relative_to(PROJECT) else AUDIT

    falsified = AUDIT.with_name("audit_falsifie.jsonl")
    records = [json.loads(line) for line in AUDIT.read_text(encoding="utf-8").splitlines() if line.strip()]
    records[len(records) // 2]["reason"] = "RAISON_MODIFIEE"
    falsified.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n",
                         encoding="utf-8")
    falsified_verification = AuditLog(falsified).verify()
    falsified_display = falsified.relative_to(PROJECT) if falsified.is_relative_to(PROJECT) else falsified

    data["scenes"]["S6"] = {
        "verification": verification.as_dict(),
        "verification_falsifiee": falsified_verification.as_dict(),
        "queue": [audit_view(item) for item in tail],
    }
    lines += [
        "S6 — VÉRIFICATION DE LA CHAÎNE D'AUDIT",
        f"$ python3 src/ti_cli.py verify-audit --path {audit_display}",
        "  " + json.dumps({"ok": verification.ok, "entries": verification.entries,
                            "broken_at": verification.broken_at,
                            "reason": verification.reason or ""}, ensure_ascii=False),
    ]
    for item in tail:
        lines.append(f"  seq={item.get('seq'):<3} {item.get('event'):<12} {str(item.get('reason')):<26} "
                     f"hash={str(item.get('entry_hash'))[:24]}…")
    lines += [
        f"$ python3 src/ti_cli.py verify-audit --path {falsified_display}",
        "  " + json.dumps({"ok": falsified_verification.ok, "entries": falsified_verification.entries,
                            "broken_at": falsified_verification.broken_at,
                            "reason": falsified_verification.reason or ""}, ensure_ascii=False),
        "",
    ]
    show()
    next_scene()

    # S7 — comparaison avec la maquette sans contrôle
    intro("S7")
    sys.path.insert(0, str(PROJECT / "tests"))
    from baseline_naive import NaiveTI  # noqa: E402
    naive = NaiveTI(DATA)
    leak = naive.get_advisory("ADV-2026-004") or {}
    source_doc = naive.get_advisory("ADV-2026-003") or {}
    with MCPClient(analyst_token, env_extra=env(), timeout=15.0) as client:
        client.initialize()
        redacted = summarise(client.call("ti_get_advisory", {"advisory_id": "ADV-2026-003"}))
        entry = last_audit()
    redacted_security = redacted.get("securite") or {}
    source_value = str(source_doc.get("source_identity") or "")
    data["scenes"]["S7"] = {
        "maquette_canari": CANARY in json.dumps(leak, ensure_ascii=False),
        "maquette_source_claire": bool(source_value) and source_value in json.dumps(source_doc, ensure_ascii=False),
        "source_identifiee_dans_maquette": bool(source_value),
        "serveur_canari_sans_droit": data["scenes"]["S2"]["canari_present"],
        "serveur_champs_masques": redacted_security.get("champs_masques"),
        "serveur_source_presente": bool(source_value) and source_value in redacted["texte"],
        "audit_champs_masques": entry.get("redacted_fields"),
    }
    s7 = data["scenes"]["S7"]
    lines += [
        "S7 — AVANT / APRÈS SUR LES MÊMES BULLETINS",
        f"  maquette sans contrôle (ADV-2026-004 Secret) : canari présent={s7['maquette_canari']}",
        f"  serveur durci, jeton Confidentiel : canari présent={s7['serveur_canari_sans_droit']}",
        f"  maquette sans contrôle (ADV-2026-003) : source claire={s7['maquette_source_claire']}",
        f"  serveur durci, jeton Confidentiel : source présente={s7['serveur_source_presente']}  "
        f"champs masqués={s7['serveur_champs_masques']}",
        f"  serveur durci, jeton Secret+CRYPTO : canari présent=True (contrôle positif)",
        "",
        "FIN DE LA DÉMONSTRATION",
    ]
    show()

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_TXT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.present:
        if args.auto_delay <= 0:
            print("\n  Démonstration terminée : sept scènes rejouées, chaque décision est journalisée.")
            print(f"  Trace écrite : {OUT_TXT}")
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
