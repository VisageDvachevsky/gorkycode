from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .constants import (
    HISTORY_HINTS,
    INDOOR_CATEGORIES,
    MORNING_AVOID_KEYWORDS,
    NIGHT_PREFERRED_KEYWORDS,
    NIGHT_UNSAFE_KEYWORDS,
    OUTDOOR_CATEGORIES,
    SOCIAL_MODE_CATEGORY_PREFS,
    STREET_ART_HINTS,
)
from .intensity import effective_visit_minutes, search_radius_km, transition_padding
from .metadata import build_metadata, contains_keywords, is_history, is_street_art, normalize
from .models import CandidateScore, WeatherSnapshot
from .time_phase import phase_category_score, resolve_time_phase


logger = logging.getLogger(__name__)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def weather_alignment_score(
    category: str, tags: Tuple[str, ...], weather: Optional[WeatherSnapshot]
) -> float:
    if weather is None:
        return 0.75
    category_key = category
    if category_key in INDOOR_CATEGORIES:
        indoor_bias = 0.92
    elif category_key in OUTDOOR_CATEGORIES:
        indoor_bias = 0.65
    else:
        indoor_bias = 0.75

    if weather.is_foggy:
        indoor_bias += 0.05 if category_key in INDOOR_CATEGORIES else -0.08
    if weather.is_precipitation:
        indoor_bias += 0.06 if category_key in INDOOR_CATEGORIES else -0.12
    if weather.temperature_c is not None and weather.temperature_c <= 2.0:
        indoor_bias += 0.04 if category_key in INDOOR_CATEGORIES else -0.06
    if weather.temperature_c is not None and weather.temperature_c >= 24.0:
        indoor_bias += -0.04 if category_key in INDOOR_CATEGORIES else 0.05

    if any("крыт" in tag for tag in tags):
        indoor_bias += 0.05
    if any("outdoor" in tag or "street" in tag for tag in tags):
        indoor_bias -= 0.04

    return clamp(indoor_bias, 0.45, 1.05)


def social_alignment_score(category: str, tags: Tuple[str, ...], social_mode: str) -> float:
    preferences = SOCIAL_MODE_CATEGORY_PREFS.get(social_mode, {"default": 0.75})
    base = preferences.get(category, preferences.get("default", 0.75))
    if social_mode == "friends" and any(
        tag for tag in tags if "инст" in tag or "инста" in tag
    ):
        base += 0.05
    if social_mode == "family" and any("дет" in tag for tag in tags):
        base += 0.04
    if social_mode == "couple" and any("панорама" in tag or "вид" in tag for tag in tags):
        base += 0.05
    if social_mode == "solo" and any("тихий" in tag or "спокой" in tag for tag in tags):
        base += 0.04
    return clamp(base, 0.5, 1.0)


def accessibility_score(distance_km: float, intensity: str) -> float:
    radius = search_radius_km(intensity)
    if distance_km <= radius * 0.35:
        return 1.0
    if distance_km <= radius * 0.65:
        return 0.85
    if distance_km <= radius * 0.9:
        return 0.7
    if distance_km <= radius * 1.15:
        return 0.55
    return 0.4


def contextual_score(
    *,
    category: str,
    tags: Tuple[str, ...],
    arrival_time: datetime,
    social_mode: str,
    intensity: str,
    distance_km: float,
    weather: Optional[WeatherSnapshot],
) -> float:
    phase = resolve_time_phase(arrival_time)
    time_alignment = phase_category_score(category, tags, phase)
    weather_alignment = weather_alignment_score(category, tags, weather)
    social_alignment = social_alignment_score(category, tags, social_mode)
    access_alignment = accessibility_score(distance_km, intensity)

    contextual = (
        0.4 * time_alignment
        + 0.25 * weather_alignment
        + 0.2 * social_alignment
        + 0.15 * access_alignment
    )
    return clamp(contextual * 100.0, 0.0, 100.0)


def embedding_component(raw_score: Optional[float]) -> float:
    if raw_score is None:
        return 55.0
    return clamp(raw_score * 100.0, 0.0, 100.0)


def popularity_component(rating: Optional[float]) -> float:
    if rating is None or rating <= 0:
        return 18.0
    normalized = clamp(rating / 5.0, 0.0, 1.0)
    return normalized * 30.0


def diversity_penalty(category: str, recent_categories: Sequence[str]) -> float:
    if not category or not recent_categories:
        return 0.0
    penalty = 0.0
    if category == recent_categories[-1]:
        penalty = 30.0
    elif category in recent_categories:
        penalty = 15.0
    return penalty


def prefilter_candidates(
    pois: Sequence,
    start_lat: float,
    start_lon: float,
    intensity: str,
    max_candidates: int = 60,
    distance_fn: Optional[Callable[[float, float], float]] = None,
) -> List:
    if len(pois) <= max_candidates:
        return list(pois)

    radius = search_radius_km(intensity)
    relaxed_radius = radius * 1.25
    near: List[Tuple[float, object]] = []
    far: List[Tuple[float, object]] = []
    for poi in pois:
        if distance_fn:
            dist = distance_fn(poi.lat, poi.lon)
        else:
            dist = math_distance(start_lat, start_lon, poi.lat, poi.lon)
        bucket = near if dist <= relaxed_radius else far
        bucket.append((dist, poi))

    near.sort(key=lambda item: item[0])
    far.sort(key=lambda item: item[0])

    ordered: List = [poi for _, poi in near[:max_candidates]]
    if len(ordered) < max_candidates:
        remaining = max_candidates - len(ordered)
        ordered.extend(poi for _, poi in far[:remaining])
    return ordered


def math_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from .geometry import haversine_km

    return haversine_km(lat1, lon1, lat2, lon2)


def prioritize_candidates(
    pois: Sequence,
    *,
    start_time: datetime,
    intensity: str,
    social_mode: str,
    start_lat: float,
    start_lon: float,
    weather: Optional[WeatherSnapshot],
) -> Tuple[List[CandidateScore], Dict[int, CandidateScore]]:
    if not pois:
        return [], {}

    slot_minutes = effective_visit_minutes(None, intensity) + transition_padding(intensity)
    slot_minutes = max(30.0, float(slot_minutes))

    enriched: List[Dict[str, Any]] = []
    for index, poi in enumerate(pois):
        arrival = start_time + timedelta(minutes=index * slot_minutes)
        category = normalize(getattr(poi, "category", "") or "")
        tags = tuple(
            normalize(tag)
            for tag in getattr(poi, "tags", [])
            if tag and isinstance(tag, str)
        )
        distance_km = math_distance(start_lat, start_lon, poi.lat, poi.lon)
        embedding_match = embedding_component(getattr(poi, "score", None))
        contextual = contextual_score(
            category=category or "unknown",
            tags=tags,
            arrival_time=arrival,
            social_mode=social_mode,
            intensity=intensity,
            distance_km=distance_km,
            weather=weather,
        )
        popularity = popularity_component(getattr(poi, "rating", None))
        base_score = (embedding_match * 0.4) + (contextual * 0.3) + (popularity * 0.15)

        enriched.append(
            {
                "poi": poi,
                "embedding": embedding_match,
                "contextual": contextual,
                "popularity": popularity,
                "base_score": base_score,
                "arrival": arrival,
                "distance": distance_km,
                "category": category or "unknown",
                "tags": tags,
            }
        )

    enriched.sort(key=lambda item: (item["base_score"], item["embedding"]), reverse=True)

    recent: List[str] = []
    scored: List[CandidateScore] = []
    score_map: Dict[int, CandidateScore] = {}

    for item in enriched:
        category = item["category"]
        penalty = diversity_penalty(category, recent[-3:])
        if penalty > 0:
            logger.info(
                "🚫 Diversity penalty %.1f for '%s' (recent: %s)",
                penalty,
                category,
                recent[-3:],
            )
        final_score = item["base_score"] - penalty * 0.15
        final_score = max(0.0, final_score)

        candidate = CandidateScore(
            poi=item["poi"],
            embedding_match=item["embedding"],
            contextual=item["contextual"],
            popularity=item["popularity"],
            base_score=item["base_score"],
            penalty=penalty,
            final_score=final_score,
            arrival_time=item["arrival"],
            distance_km=item["distance"],
            category=category,
            tags=item["tags"],
        )

        scored.append(candidate)
        poi_id = getattr(item["poi"], "poi_id", None)
        if poi_id is not None:
            score_map[int(poi_id)] = candidate

        recent.append(category)
        if len(recent) > 3:
            recent[:] = recent[-3:]

    scored.sort(key=lambda entry: (entry.final_score, entry.embedding_match), reverse=True)
    return scored, score_map


def alternate_street_history_candidates(pois: Sequence) -> List:
    if not pois:
        return []

    typed = [(poi, build_metadata(poi)) for poi in pois]
    street = [poi for poi, meta in typed if is_street_art(meta)]
    history = [poi for poi, meta in typed if is_history(meta)]

    if not street or not history:
        return list(pois)

    alternated: List = []
    idx_street = idx_history = 0
    toggle = True
    while idx_street < len(street) or idx_history < len(history):
        if toggle and idx_street < len(street):
            alternated.append(street[idx_street])
            idx_street += 1
        elif idx_history < len(history):
            alternated.append(history[idx_history])
            idx_history += 1
        toggle = not toggle

    remaining = [poi for poi, _ in typed if poi not in alternated]
    alternated.extend(remaining)
    return alternated


def needs_street_history_mix(request) -> bool:
    interests = [request.interests or ""]
    if request.categories:
        interests.extend(request.categories)
    combined = " ".join(interests).lower()
    return (
        any(keyword in combined for keyword in STREET_ART_HINTS)
        and any(keyword in combined for keyword in HISTORY_HINTS)
    )


def apply_time_window_filters(
    pois: Sequence,
    start_time: Optional[datetime],
    *,
    start_hour: Optional[int] = None,
) -> List:
    entries = list(pois)
    if not entries:
        return entries

    from .schedule import resolve_start_reference, availability_score_for_start

    resolved_start, resolved_hour = resolve_start_reference(start_time, start_hour)
    metadata_entries = [(poi, build_metadata(poi)) for poi in entries]

    filtered_entries: List[Tuple[object, object]] = []
    for poi, meta in metadata_entries:
        if resolved_hour < 9 and contains_keywords(
            meta.keywords, MORNING_AVOID_KEYWORDS, pre_normalized=True
        ):
            continue
        if resolved_hour >= 21 and contains_keywords(
            meta.keywords, NIGHT_UNSAFE_KEYWORDS, pre_normalized=True
        ):
            continue
        filtered_entries.append((poi, meta))

    if not filtered_entries:
        filtered_entries = metadata_entries

    scored: List[Tuple[float, float, object]] = []
    for poi, meta in filtered_entries:
        base_score = availability_score_for_start(poi, resolved_start)
        preference_bonus = 0.0
        if resolved_hour >= 21 and contains_keywords(
            meta.keywords, NIGHT_PREFERRED_KEYWORDS, pre_normalized=True
        ):
            preference_bonus = 0.08
        rating = float(getattr(poi, "rating", 0.0) or 0.0)
        scored.append((min(1.1, base_score + preference_bonus), rating, poi))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [entry[2] for entry in scored]
