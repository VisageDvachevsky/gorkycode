from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import httpx

from .intensity import minutes_from_distance, WALK_SPEED_KMH

logger = logging.getLogger(__name__)


@dataclass
class LegEstimate:
    distance_km: float
    duration_minutes: float
    geometry: List[Tuple[float, float]]
    maneuvers: List[dict]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


class OSRMClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._available = True
        self._timeout = httpx.Timeout(5.0, connect=2.0)

    async def route(
        self,
        start: Tuple[float, float],
        waypoints: Sequence[Tuple[float, float]],
        profile: str = "foot",
    ) -> Tuple[List[LegEstimate], List[Tuple[float, float]]]:
        if not waypoints:
            return [], [(float(start[0]), float(start[1]))]

        if not self._available:
            raise RuntimeError("OSRM client disabled after previous failure")

        coords = [start, *waypoints]
        coord_pairs = [f"{lon},{lat}" for lat, lon in coords]
        url = f"{self.base_url}/route/v1/{profile}/" + ";".join(coord_pairs)
        params = {
            "steps": "true",
            "geometries": "geojson",
            "overview": "full",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.debug("OSRM request failed: %s", exc)
            self._available = False
            raise RuntimeError("OSRM request failed") from exc
        except Exception as exc:
            logger.debug("Unexpected OSRM failure: %s", exc)
            self._available = False
            raise

        payload = response.json()
        routes = payload.get("routes") or []
        if not routes:
            self._available = False
            raise RuntimeError("OSRM returned no routes")

        route_payload = routes[0]
        legs_payload = route_payload.get("legs") or []
        coordinates = route_payload.get("geometry", {}).get("coordinates", [])

        geometry = [(float(lat), float(lon)) for lon, lat in coordinates]
        leg_estimates: List[LegEstimate] = []
        current_cursor = start
        for leg in legs_payload:
            distance_m = float(leg.get("distance", 0.0))
            duration_s = float(leg.get("duration", 0.0))
            distance_km = max(distance_m / 1000.0, 0.0)
            if duration_s <= 0:
                duration_minutes = minutes_from_distance(distance_km, WALK_SPEED_KMH)
            else:
                duration_minutes = max(duration_s / 60.0, 0.0)

            steps = leg.get("steps") or []
            step_coords: List[Tuple[float, float]] = []
            maneuvers: List[dict] = []
            for step in steps:
                step_geometry = step.get("geometry", {}).get("coordinates", [])
                for lon, lat in step_geometry:
                    step_coords.append((float(lat), float(lon)))
                maneuver = step.get("maneuver") or {}
                instruction = step.get("name") or step.get("ref") or ""
                maneuvers.append(
                    {
                        "instruction": instruction,
                        "type": maneuver.get("type"),
                        "modifier": maneuver.get("modifier"),
                        "location": maneuver.get("location"),
                        "distance": step.get("distance"),
                        "duration": step.get("duration"),
                        "street_name": step.get("name"),
                    }
                )
            if not step_coords:
                target = waypoints[len(leg_estimates)]
                step_coords = [
                    (float(current_cursor[0]), float(current_cursor[1])),
                    (float(target[0]), float(target[1])),
                ]

            leg_estimates.append(
                LegEstimate(
                    distance_km=distance_km,
                    duration_minutes=duration_minutes,
                    geometry=step_coords,
                    maneuvers=maneuvers,
                )
            )
            current_cursor = waypoints[len(leg_estimates) - 1]

        return leg_estimates, geometry


def nearest_neighbor_order(
    start: Tuple[float, float],
    points: Sequence[Tuple[float, float]],
) -> List[int]:
    remaining = set(range(len(points)))
    order: List[int] = []
    current_lat, current_lon = start
    while remaining:
        nearest_idx = min(
            remaining,
            key=lambda idx: haversine_km(
                current_lat,
                current_lon,
                points[idx][0],
                points[idx][1],
            ),
        )
        order.append(nearest_idx)
        remaining.remove(nearest_idx)
        current_lat, current_lon = points[nearest_idx]
    return order


def two_opt(order: List[int], start: Tuple[float, float], points: Sequence[Tuple[float, float]]) -> List[int]:
    improved = True
    best_order = order[:]
    while improved:
        improved = False
        for i in range(1, len(best_order) - 1):
            for j in range(i + 1, len(best_order)):
                if j - i == 1:
                    continue
                new_order = best_order[:]
                new_order[i:j] = reversed(best_order[i:j])
                if route_length(new_order, start, points) + 1e-6 < route_length(best_order, start, points):
                    best_order = new_order
                    improved = True
        order = best_order[:]
    return best_order


def route_length(order: Sequence[int], start: Tuple[float, float], points: Sequence[Tuple[float, float]]) -> float:
    total = 0.0
    current = start
    for idx in order:
        point = points[idx]
        total += haversine_km(current[0], current[1], point[0], point[1])
        current = point
    return total


def optimize_sequence(start: Tuple[float, float], points: Sequence[Tuple[float, float]]) -> List[int]:
    if not points:
        return []
    initial = nearest_neighbor_order(start, points)
    return two_opt(initial, start, points)
