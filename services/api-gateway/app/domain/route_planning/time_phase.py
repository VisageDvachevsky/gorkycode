from __future__ import annotations

from datetime import datetime
from typing import Tuple

from .constants import TIME_PHASES, TIME_PHASE_CATEGORY_PREFS


def resolve_time_phase(arrival: datetime) -> str:
    hour = arrival.hour
    for phase, start, end in TIME_PHASES:
        if start <= hour < end:
            return phase
    return "default"


def phase_category_score(category: str, tags: Tuple[str, ...], phase: str) -> float:
    preferences = TIME_PHASE_CATEGORY_PREFS.get(phase) or TIME_PHASE_CATEGORY_PREFS["default"]
    normalized = (category or "").strip().lower()
    if normalized in preferences:
        return preferences[normalized]
    for tag in tags:
        lowered = tag.lower()
        if lowered in preferences:
            return preferences[lowered]
    return preferences.get("default", 0.75)
