from __future__ import annotations

from datetime import datetime, timedelta
from datetime import datetime, timedelta
from typing import Awaitable, Callable, Optional, Sequence, Tuple

from app.models.schemas import CoffeePreferences, POIInRoute

from .intensity import effective_visit_minutes, recommended_break_interval_minutes, transition_padding
from .geometry import haversine_km, minutes_from_distance


def recommended_interval(intensity: str, preferences: Optional[CoffeePreferences]) -> int:
    baseline = recommended_break_interval_minutes(intensity)
    if not preferences or not preferences.enabled:
        return baseline
    configured = max(30, preferences.interval_minutes)
    return max(baseline, configured)


def estimate_coffee_break_minutes(
    total_minutes: float,
    *,
    intensity: str,
    preferences: Optional[CoffeePreferences],
) -> float:
    if not preferences or not preferences.enabled or total_minutes <= 0:
        return 0.0
    interval = float(recommended_interval(intensity, preferences))
    if total_minutes < interval * 0.75:
        return 0.0
    breaks = int(total_minutes // interval)
    remainder = total_minutes - breaks * interval
    if remainder >= interval * 0.6:
        breaks += 1
    breaks = max(1, breaks)
    breaks = min(breaks, max(1, int(total_minutes // 105) + 1))
    base_stay = max(18, min(35, interval / 3.2))
    stay_minutes = effective_visit_minutes(int(round(base_stay)), intensity)
    return float(breaks * stay_minutes)


async def maybe_add_coffee_break(
    *,
    preferences: CoffeePreferences,
    current_lat: float,
    current_lon: float,
    cursor_time: datetime,
    order_number: int,
    intensity: str,
    fetch_cafes: Callable[[float, float, float], Awaitable[Sequence]],
) -> Optional[Tuple[POIInRoute, datetime, float, float, float]]:
    radius = preferences.search_radius_km or 0.6

    try:
        cafes = await fetch_cafes(current_lat, current_lon, radius)
    except Exception:
        return None

    cafes = list(cafes)
    if not cafes:
        return None

    cafe = min(cafes, key=lambda c: getattr(c, "distance", 0.0) or 0.0)
    walk_km = haversine_km(current_lat, current_lon, cafe.lat, cafe.lon)
    walk_minutes = minutes_from_distance(walk_km)
    arrival_time = cursor_time + timedelta(minutes=walk_minutes)

    stay_minutes = max(15, min(30, preferences.interval_minutes // 3))
    stay_minutes = effective_visit_minutes(stay_minutes, intensity)
    padding = transition_padding(intensity)
    leave_time = arrival_time + timedelta(minutes=stay_minutes + padding)

    why = f"Сделайте паузу в {cafe.name}: уютное место неподалёку для кофе и отдыха."
    tip_parts = ["Возьмите напиток, чтобы зарядиться перед следующими точками."]
    address = getattr(cafe, "address", None)
    if address:
        tip_parts.append(f"Адрес: {address}.")
    tip = " ".join(tip_parts)

    coffee_item = POIInRoute(
        order=order_number,
        poi_id=stable_coffee_id(getattr(cafe, "id", None) or cafe.name),
        name=cafe.name,
        lat=cafe.lat,
        lon=cafe.lon,
        why=why,
        tip=tip,
        est_visit_minutes=stay_minutes,
        arrival_time=arrival_time,
        leave_time=leave_time,
        is_coffee_break=True,
        category="coffee_break",
        tags=["coffee", "break"],
        emoji="☕",
        distance_from_previous_km=round(walk_km, 2),
    )

    return coffee_item, leave_time, cafe.lat, cafe.lon, walk_km


def stable_coffee_id(source_id: str) -> int:
    import hashlib

    digest = hashlib.sha1(source_id.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16)
