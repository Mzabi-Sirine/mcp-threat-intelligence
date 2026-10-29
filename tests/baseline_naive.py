"""Maquette témoin volontairement naïve : sert uniquement de comparatif « avant ».

Elle ne contient aucun contrôle d'accès, aucun assainissement, aucune trace.
Elle n'est jamais exposée comme serveur : elle montre ce qui se passerait sans
les contrôles du projet.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class NaiveTI:
    def __init__(self, data_dir: Path | str):
        data_dir = Path(data_dir)
        self.advisories = [json.loads(line) for line in (data_dir / "advisories.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.iocs = [json.loads(line) for line in (data_dir / "iocs.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assets = json.loads((data_dir / "assets.json").read_text(encoding="utf-8"))

    def search(self, query: str) -> list[dict[str, Any]]:
        query = query.lower()
        if query == "*":
            return list(self.advisories)
        return [
            doc for doc in self.advisories
            if query in (doc["id"] + doc["title"] + doc["summary"] + doc["body"]).lower()
        ]

    def get_advisory(self, advisory_id: str) -> dict[str, Any] | None:
        return next((doc for doc in self.advisories if doc["id"] == advisory_id), None)

    def enrich_ioc(self, value: str) -> dict[str, Any] | None:
        return next((ioc for ioc in self.iocs if ioc["value"] == value), None)

    def score_asset(self, asset_id: str) -> dict[str, Any] | None:
        return next((asset for asset in self.assets if asset["id"] == asset_id), None)
