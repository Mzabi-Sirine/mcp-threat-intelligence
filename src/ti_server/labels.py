"""Treillis d'étiquettes et règles de cloisonnement."""
from __future__ import annotations

from .config import LEVEL_BY_NAME, LEVELS, TLP_BY_NAME


class LabelError(ValueError):
    pass


def parse_level(value: object) -> int:
    if isinstance(value, bool):
        raise LabelError("niveau de classification invalide")
    if isinstance(value, int):
        level = value
    elif isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            level = int(text)
        else:
            key = text.lower()
            if key not in LEVEL_BY_NAME and key not in TLP_BY_NAME:
                raise LabelError(f"niveau inconnu: {value}")
            level = LEVEL_BY_NAME.get(key, TLP_BY_NAME.get(key, -1))
    else:
        raise LabelError("niveau de classification invalide")
    if level not in LEVELS:
        raise LabelError("niveau hors barème 0..3")
    return level


def max_level(levels: list[int], default: int = 0) -> int:
    return max(levels) if levels else default


def clearance_covers(clearance: int, classification: int) -> bool:
    return int(clearance) >= int(classification)


def compartments_cover(owned: list[str], required: list[str]) -> bool:
    owned_set = {str(item).strip().upper() for item in owned or [] if str(item).strip()}
    required_set = {str(item).strip().upper() for item in required or [] if str(item).strip()}
    return required_set.issubset(owned_set)


def normalize_compartment(value: str) -> str:
    return str(value).strip().upper()
