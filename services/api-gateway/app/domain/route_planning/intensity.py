from __future__ import annotations

from typing import Dict

from .constants import (
    INTENSITY_CANDIDATE_MULTIPLIER,
    INTENSITY_PROFILES,
    INTENSITY_SEARCH_RADIUS_KM,
    RECOMMENDED_COFFEE_INTERVAL,
)

WALK_SPEED_KMH = 4.5
DEFAULT_VISIT_MINUTES = 45


def get_intensity_profile(intensity: str) -> Dict[str, float]:
    try:
        return INTENSITY_PROFILES[intensity]
    except KeyError:
        return INTENSITY_PROFILES["medium"]


def transition_padding(intensity: str) -> float:
    return get_intensity_profile(intensity)["transition_padding"]


def safety_buffer_minutes(intensity: str) -> float:
    return get_intensity_profile(intensity)["safety_buffer"]


def minutes_from_distance(distance_km: float, base_speed: float = WALK_SPEED_KMH) -> float:
    if distance_km <= 0:
        return 0.0
    if base_speed <= 0:
        base_speed = WALK_SPEED_KMH
    return distance_km / base_speed * 60.0


def effective_visit_minutes(base_minutes: int | None, intensity: str) -> int:
    profile = get_intensity_profile(intensity)
    if base_minutes is None or base_minutes <= 0:
        baseline = profile["default_visit_minutes"]
    else:
        baseline = float(base_minutes)
    bounded = max(profile["min_visit_minutes"], min(baseline, profile["max_visit_minutes"]))
    return int(round(bounded))


def candidate_multiplier(intensity: str) -> float:
    return INTENSITY_CANDIDATE_MULTIPLIER.get(intensity, 2.0)


def search_radius_km(intensity: str) -> float:
    return INTENSITY_SEARCH_RADIUS_KM.get(intensity, 6.0)


def recommended_break_interval_minutes(intensity: str) -> int:
    return RECOMMENDED_COFFEE_INTERVAL.get(intensity, 105)
