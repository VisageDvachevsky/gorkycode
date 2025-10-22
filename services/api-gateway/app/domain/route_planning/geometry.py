from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import httpx

from .intensity import WALK_SPEED_KMH, minutes_from_distance

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


class TwoGISRoutingClient:
    ROUTING_URL = "https://routing.api.2gis.com/routing/7.0.0/global"

    def __init__(
        self,
        api_key: str | None,
        *,
        locale: str = "ru_RU",
        route_locale: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.locale = locale
        self.route_locale = route_locale or locale
        self._timeout = httpx.Timeout(timeout, connect=10.0)
        self._enabled = bool(api_key)

    def is_enabled(self) -> bool:
        return self._enabled and bool(self.api_key)

    async def route_leg(
        self, start: Tuple[float, float], end: Tuple[float, float]
    ) -> LegEstimate:
        route = await self._request(points=[start, end])
        return self._build_estimate(route, start, end)

    async def route_sequence(
        self, start: Tuple[float, float], waypoints: Sequence[Tuple[float, float]]
    ) -> List[LegEstimate]:
        legs: List[LegEstimate] = []
        cursor = start
        for target in waypoints:
            legs.append(await self.route_leg(cursor, target))
            cursor = target
        return legs

    async def _request(self, points: Sequence[Tuple[float, float]]) -> dict:
        if not self.api_key:
            raise RuntimeError("TWOGIS_API_KEY is not configured")

        formatted = []
        last_index = len(points) - 1
        for idx, (lat, lon) in enumerate(points):
            point_type = "stop" if idx in (0, last_index) else "via"
            formatted.append({"type": point_type, "lat": float(lat), "lon": float(lon)})

        payload = {
            "points": formatted,
            "transport": "pedestrian",
            "route_mode": "fastest",
            "output": "detailed",
        }

        params = {
            "key": self.api_key,
            "locale": self.locale,
            "route_locale": self.route_locale,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self.ROUTING_URL, params=params, json=payload)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - network failure fallback
            self._enabled = False
            logger.warning("2GIS routing request failed: %s", exc)
            raise RuntimeError("2GIS routing request failed") from exc
        except Exception as exc:  # pragma: no cover - defensive
            self._enabled = False
            logger.warning("Unexpected 2GIS routing failure: %s", exc)
            raise RuntimeError("2GIS routing request failed") from exc

        result = data.get("result")
        if isinstance(result, list):
            result = result[0] if result else None

        if not isinstance(result, dict):
            raise RuntimeError("2GIS routing returned empty result")

        return result

    def _build_estimate(
        self,
        route: dict,
        start: Tuple[float, float],
        end: Tuple[float, float],
    ) -> LegEstimate:
        geometry = self._parse_geometry(route)
        if not geometry:
            geometry = [(float(start[0]), float(start[1])), (float(end[0]), float(end[1]))]

        distance_km = float(route.get("distance", 0.0)) / 1000.0
        if distance_km <= 0:
            distance_km = haversine_km(start[0], start[1], end[0], end[1])

        duration_minutes = float(route.get("duration", 0.0)) / 60.0
        if duration_minutes <= 0:
            duration_minutes = minutes_from_distance(distance_km)

        maneuvers = self._parse_maneuvers(route)

        return LegEstimate(
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            geometry=[(float(lat), float(lon)) for lat, lon in geometry],
            maneuvers=maneuvers,
        )

    def _parse_geometry(self, route: dict) -> List[Tuple[float, float]]:
        maneuvers = route.get("maneuvers", [])
        collected: List[Tuple[float, float]] = []
        seen = set()

        for maneuver in maneuvers:
            path = maneuver.get("outcoming_path", {})
            for segment in path.get("geometry", []):
                selection = segment.get("selection", "")
                if selection.startswith("LINESTRING"):
                    for lat, lon in self._parse_wkt(selection):
                        key = (round(lat, 6), round(lon, 6))
                        if key not in seen:
                            seen.add(key)
                            collected.append((lat, lon))

        if collected:
            return collected

        waypoints = route.get("waypoints", [])
        for waypoint in waypoints:
            point = waypoint.get("projected_point") or waypoint.get("original_point")
            if point and "lat" in point and "lon" in point:
                key = (round(point["lat"], 6), round(point["lon"], 6))
                if key not in seen:
                    seen.add(key)
                    collected.append((point["lat"], point["lon"]))

        return collected

    def _parse_maneuvers(self, route: dict) -> List[dict]:
        maneuvers: List[dict] = []
        for maneuver in route.get("maneuvers", []):
            instruction = (
                maneuver.get("instruction", {}).get("text")
                or maneuver.get("action", {}).get("text")
                or maneuver.get("comment", "")
            )
            if not instruction:
                continue

            distance = maneuver.get("distance")
            if distance is None:
                distance = maneuver.get("outcoming_path", {}).get("length")

            duration = maneuver.get("duration")

            maneuvers.append(
                {
                    "instruction": instruction,
                    "street_name": maneuver.get("street_name")
                    or maneuver.get("road_name")
                    or "",
                    "distance": float(distance) if distance is not None else 0.0,
                    "duration": float(duration) if duration is not None else 0.0,
                }
            )

        return maneuvers

    def _parse_wkt(self, wkt: str) -> List[Tuple[float, float]]:
        try:
            coords = wkt.replace("LINESTRING(", "").replace(")", "")
            pairs = coords.split(",")
            result: List[Tuple[float, float]] = []
            for pair in pairs:
                lon_str, lat_str = pair.strip().split()[:2]
                result.append((float(lat_str), float(lon_str)))
            return result
        except Exception:  # pragma: no cover - defensive parsing guard
            logger.debug("Failed to parse WKT geometry: %s", wkt[:80])
            return []


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

