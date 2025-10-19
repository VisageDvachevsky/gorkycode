import importlib
import sys
from pathlib import Path

import numpy as np
import pytest

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

_removed_modules = {
    name: sys.modules.pop(name)
    for name in list(sys.modules.keys())
    if name == "app" or name.startswith("app.")
}

RoutePlannerModule = importlib.import_module("app.services.route_planner_engine")
RoutingModule = importlib.import_module("app.services.routing")

sys.modules.update(_removed_modules)

RoutePOI = RoutePlannerModule.RoutePOI
RoutePlanner = RoutePlannerModule.RoutePlanner
routing_service = RoutingModule.routing_service


@pytest.mark.asyncio
async def test_optimize_route_with_distance_matrix(monkeypatch):
    planner = RoutePlanner()

    pois = [
        RoutePOI(id=1, name="A", lat=56.31, lon=43.95, avg_visit_minutes=30),
        RoutePOI(id=2, name="B", lat=56.32, lon=43.96, avg_visit_minutes=25),
    ]

    matrix = np.array([
        [0.0, 0.8, 1.2],
        [0.8, 0.0, 0.6],
        [1.2, 0.6, 0.0],
    ])

    async def fake_matrix(*args, **kwargs):
        return matrix

    monkeypatch.setattr(planner, "_get_real_distance_matrix", fake_matrix)

    route, distance = await planner.optimize_route(56.30, 43.94, pois, available_hours=5)

    assert [poi.id for poi in route] == [1, 2]
    assert distance == pytest.approx(1.4)


@pytest.mark.asyncio
async def test_optimize_route_haversine_fallback(monkeypatch):
    planner = RoutePlanner()

    pois = [
        RoutePOI(id=1, name="A", lat=56.31, lon=43.95, avg_visit_minutes=15),
        RoutePOI(id=2, name="B", lat=56.32, lon=43.94, avg_visit_minutes=15),
    ]

    async def no_matrix(*args, **kwargs):
        return None

    monkeypatch.setattr(planner, "_get_real_distance_matrix", no_matrix)
    monkeypatch.setattr(
        routing_service,
        "calculate_distance_km",
        lambda lat1, lon1, lat2, lon2: 1.0,
    )

    route, distance = await planner.optimize_route(56.30, 43.90, pois, available_hours=2)

    assert route  # fallback still returns route
    assert distance > 0


def test_greedy_skips_overbudget_and_unreachable():
    planner = RoutePlanner()

    pois = [
        RoutePOI(id=1, name="Far", lat=0.0, lon=0.0, avg_visit_minutes=120),
        RoutePOI(id=2, name="Near", lat=0.0, lon=0.0, avg_visit_minutes=20),
        RoutePOI(id=3, name="Blocked", lat=0.0, lon=0.0, avg_visit_minutes=15),
    ]

    matrix = np.array(
        [
            [0.0, 5.0, 1.0, np.inf],
            [5.0, 0.0, 1.0, np.inf],
            [1.0, 1.0, 0.0, np.inf],
            [np.inf, np.inf, np.inf, 0.0],
        ]
    )

    route, total_time, total_distance = planner._greedy_nearest_neighbor(
        matrix, pois, available_minutes=60
    )

    assert [pois[i].id for i in route] == [2]
    assert total_time == planner.calculate_walk_time_minutes(1.0) + pois[1].avg_visit_minutes
    assert total_distance == pytest.approx(1.0)
