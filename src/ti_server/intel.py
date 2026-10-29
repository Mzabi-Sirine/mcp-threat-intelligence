"""Calculs de renseignement : score composite, décroissance, corrélation."""
from __future__ import annotations

import datetime as dt
from typing import Any

from .config import CONFIDENCE_HALF_LIFE_DAYS, label_name, parse_ts, tlp_name


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def risk_score(cvss: float, epss: float, kev: bool, criticality: int, exposure: int) -> dict[str, Any]:
    cvss = _clamp(float(cvss), 0.0, 10.0)
    epss = _clamp(float(epss), 0.0, 1.0)
    criticality = int(_clamp(int(criticality), 1, 5))
    exposure = int(_clamp(int(exposure), 1, 5))
    threat = 0.50 * (cvss / 10.0) + 0.30 * epss + 0.20 * (1.0 if kev else 0.0)
    asset_factor = 0.6 * (criticality / 5.0) + 0.4 * (exposure / 5.0)
    score = round(10.0 * threat * (0.5 + 0.5 * asset_factor), 2)
    if score >= 8.5:
        priority = "P1"
    elif score >= 7.0:
        priority = "P2"
    elif score >= 4.5:
        priority = "P3"
    else:
        priority = "P4"
    return {
        "score": score,
        "priorite": priority,
        "composantes": {
            "menace": round(threat, 4),
            "facteur_actif": round(asset_factor, 4),
            "cvss": cvss,
            "epss": epss,
            "kev": bool(kev),
            "criticite": criticality,
            "exposition": exposure,
        },
        "formule": "10 x menace x (0,5 + 0,5 x facteur_actif)",
        "version_moteur": "score-1.0",
    }


def effective_confidence(confidence: float, first_seen: str, now: dt.datetime | None = None) -> float:
    now = now or dt.datetime.now(dt.timezone.utc)
    seen = parse_ts(first_seen)
    age_days = max(0.0, (now - seen).total_seconds() / 86400.0)
    value = float(confidence) * (0.5 ** (age_days / CONFIDENCE_HALF_LIFE_DAYS))
    return round(_clamp(value, 0.0, 1.0), 4)


def enrich_ioc(ioc: dict[str, Any], advisories: list[dict[str, Any]], now: dt.datetime | None = None) -> dict[str, Any]:
    now = now or dt.datetime.now(dt.timezone.utc)
    related = [adv for adv in advisories if adv["id"] in set(ioc.get("advisory_ids", []))]
    effective = effective_confidence(ioc["confidence"], ioc["first_seen"], now)
    source_trust = max((float(adv.get("source_trust", 0.0)) for adv in related), default=0.5)
    contextual = round(effective * (0.5 + 0.5 * source_trust), 4)
    labels = [int(adv["classification"]) for adv in related] or [int(ioc["classification"])]
    return {
        "indicateur": ioc["value"],
        "type": ioc["type"],
        "famille": ioc["family"],
        "etiquettes": ioc["tags"],
        "confiance_source": ioc["confidence"],
        "confiance_effective": effective,
        "confiance_contextuelle": contextual,
        "demi_vie_jours": CONFIDENCE_HALF_LIFE_DAYS,
        "premiere_observation": ioc["first_seen"],
        "source": ioc["source"],
        "bulletins_lies": [
            {
                "id": adv["id"],
                "titre": adv["title"],
                "niveau": label_name(int(adv["classification"])),
                "publication": adv["published_at"],
            }
            for adv in sorted(related, key=lambda item: item["published_at"], reverse=True)
        ],
        "niveau_agrege": label_name(max(labels)),
        "tlp_agrege": tlp_name(max(labels)),
    }


def correlate(iocs: list[dict[str, Any]], now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    groups: dict[str, list[dict[str, Any]]] = {}
    for ioc in iocs:
        groups.setdefault(ioc["family"], []).append(ioc)
    clusters: list[dict[str, Any]] = []
    for family, members in groups.items():
        tags: dict[str, int] = {}
        types: dict[str, int] = {}
        advisory_ids: set[str] = set()
        for item in members:
            for tag in item.get("tags", []):
                tags[tag] = tags.get(tag, 0) + 1
            types[item["type"]] = types.get(item["type"], 0) + 1
            advisory_ids.update(item.get("advisory_ids", []))
        confidences = [effective_confidence(item["confidence"], item["first_seen"], now) for item in members]
        labels = [int(item["classification"]) for item in members]
        clusters.append(
            {
                "famille": family,
                "nombre_indicateurs": len(members),
                "types": types,
                "tags_dominants": [tag for tag, _ in sorted(tags.items(), key=lambda pair: (-pair[1], pair[0]))[:5]],
                "confiance_effective_moyenne": round(sum(confidences) / len(confidences), 4),
                "premiere_observation": min(item["first_seen"] for item in members),
                "derniere_observation": max(item["first_seen"] for item in members),
                "bulletins_lies": sorted(advisory_ids),
                "niveau_agrege": label_name(max(labels)),
                "tlp_agrege": tlp_name(max(labels)),
            }
        )
    return sorted(clusters, key=lambda item: (-item["nombre_indicateurs"], item["famille"]))
