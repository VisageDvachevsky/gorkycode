import itertools
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

fake_common = ModuleType("ai_tourist_common")
fake_common.get_trace_id = lambda: "-"
sys.modules.setdefault("ai_tourist_common", fake_common)

from app.domain.route_planning.diversity import enforce_category_diversity
from app.domain.route_planning.geometry import haversine_km
from app.domain.route_planning.optimization import optimize_poi_sequence
from app.domain.route_planning.schedule import is_open_at


def _route_length(start_lat: float, start_lon: float, pois: list[SimpleNamespace]) -> float:
    total = 0.0
    cursor = (start_lat, start_lon)
    for poi in pois:
        total += haversine_km(cursor[0], cursor[1], poi.lat, poi.lon)
        cursor = (poi.lat, poi.lon)
    return total


def test_optimize_poi_sequence_matches_optimum_for_small_routes():
    start_lat, start_lon = 56.3268, 44.0059
    pois = [
        SimpleNamespace(id=1, lat=56.3275, lon=44.0062),
        SimpleNamespace(id=2, lat=56.3281, lon=44.0083),
        SimpleNamespace(id=3, lat=56.3302, lon=44.0105),
        SimpleNamespace(id=4, lat=56.3310, lon=44.0128),
    ]

    optimized = optimize_poi_sequence(pois, start_lat, start_lon)
    optimized_length = _route_length(start_lat, start_lon, optimized)

    best_length = min(
        _route_length(start_lat, start_lon, list(order)) for order in itertools.permutations(pois)
    )

    assert optimized_length == pytest.approx(best_length, rel=1e-6)


def test_enforce_category_diversity_limits_streaks():
    pois = [
        SimpleNamespace(id=1, category="museum"),
        SimpleNamespace(id=2, category="museum"),
        SimpleNamespace(id=3, category="museum"),
        SimpleNamespace(id=4, category="park"),
        SimpleNamespace(id=5, category="museum"),
    ]

    diversified = enforce_category_diversity(pois, max_consecutive=2)

    assert {poi.id for poi in diversified} == {poi.id for poi in pois}

    streak = 1
    for previous, current in zip(diversified, diversified[1:]):
        if previous.category == current.category:
            streak += 1
        else:
            streak = 1
        assert streak <= 2


def test_is_open_at_uses_opening_hours_windows():
    poi = SimpleNamespace(
        category="museum",
        opening_hours="Mo-Fr 10:00-18:00; Sa-Su 11:00-16:00",
        open_time=None,
        close_time=None,
    )

    monday_morning = datetime(2024, 1, 1, 9, 30)
    can_visit, wait_minutes = is_open_at(poi, monday_morning, max_wait_minutes=45)
    assert can_visit is True
    assert wait_minutes == pytest.approx(30, abs=1e-3)

    monday_late = datetime(2024, 1, 1, 19, 0)
    can_visit, wait_minutes = is_open_at(poi, monday_late, max_wait_minutes=45)
    assert can_visit is False
    assert wait_minutes >= 0

    sunday_morning = datetime(2024, 1, 7, 10, 30)
    can_visit, wait_minutes = is_open_at(poi, sunday_morning, max_wait_minutes=45)
    assert can_visit is True
    assert wait_minutes == pytest.approx(30, abs=1e-3)

    fallback_poi = SimpleNamespace(
        category="park",
        opening_hours=None,
        open_time="09:00",
        close_time="21:00",
    )
    afternoon = datetime(2024, 1, 2, 14, 0)
    can_visit, wait_minutes = is_open_at(fallback_poi, afternoon)
    assert can_visit is True
    assert wait_minutes == pytest.approx(0.0, abs=1e-6)

    late_night = datetime(2024, 1, 2, 22, 30)
    can_visit, wait_minutes = is_open_at(fallback_poi, late_night)
    assert can_visit is False
    assert wait_minutes >= 0
