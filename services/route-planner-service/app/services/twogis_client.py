"""Async 2GIS API client used by the route planner service."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)


class TwoGISClient:
    """Thin async wrapper around 2GIS HTTP APIs with Redis caching."""

    ROUTING_URL = "https://routing.api.2gis.com/routing/7.0.0/global"
    DISTANCE_MATRIX_URL = "https://routing.api.2gis.com/get_dist_matrix"
    PUBLIC_TRANSPORT_URL = "https://routing.api.2gis.com/public/7.0.0/global"

    def __init__(self) -> None:
        self.api_key = settings.TWOGIS_API_KEY
        self.redis_client: Optional[redis.Redis] = None

        if not self.api_key:
            logger.warning("2GIS API key is not configured – routing requests will fail")

    async def connect_redis(self) -> None:
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
            logger.info("2GIS client: connected to Redis cache")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        payload = json.dumps(params, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"2gis:{prefix}:{digest}"

    async def _get_cached(self, key: str) -> Optional[Any]:
        if not self.redis_client:
            await self.connect_redis()

        cached = await self.redis_client.get(key)  # type: ignore[assignment]
        if cached:
            return json.loads(cached)
        return None

    async def _set_cache(self, key: str, value: Any, ttl: int = 3600) -> None:
        if not self.redis_client:
            await self.connect_redis()

        await self.redis_client.set(key, json.dumps(value), ex=ttl)  # type: ignore[arg-type]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _request_post(
        self,
        url: str,
        params: Dict[str, Any],
        json_body: Dict[str, Any],
        timeout: int = 45,
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None

        params = dict(params)
        params["key"] = self.api_key

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(url, params=params, json=json_body)
            except httpx.TimeoutException as exc:  # pragma: no cover - network
                logger.error("2GIS request timeout: %s", url)
                raise exc

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429:
            logger.warning("2GIS rate limit reached for %s", url)
            raise httpx.HTTPError("rate-limit")

        logger.error("2GIS error %s: %s", response.status_code, response.text)
        return None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    async def get_walking_route(
        self, points: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        """Request a walking route with full geometry between points."""

        if len(points) < 2:
            return None

        if len(points) > 10:
            # Free tier limitation – keep deterministic subset of points.
            logger.warning("Too many waypoints (%s), sampling down to 10", len(points))
            indices = [0]
            step = max(1, (len(points) - 2) // 8)
            for idx in range(step, len(points) - 1, step):
                if len(indices) >= 9:
                    break
                indices.append(idx)
            indices.append(len(points) - 1)
            points = [points[i] for i in sorted(set(indices))]

        cache_key = self._cache_key("walk", {"points": points})
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        formatted = []
        for idx, (lat, lon) in enumerate(points):
            point_type = "stop" if idx in (0, len(points) - 1) else "via"
            formatted.append({"type": point_type, "lat": lat, "lon": lon})

        request_body = {
            "points": formatted,
            "transport": "pedestrian",
            "route_mode": "fastest",
            "output": "detailed",
        }

        data = await self._request_post(self.ROUTING_URL, params={}, json_body=request_body)
        if not data or "result" not in data:
            return None

        result = data["result"]
        if isinstance(result, list):
            result = result[0] if result else None

        if result:
            await self._set_cache(cache_key, result, ttl=settings.ROUTING_CACHE_TTL_SECONDS)
        return result

    async def get_public_transport_route(
        self, start: Tuple[float, float], end: Tuple[float, float]
    ) -> Optional[Dict[str, Any]]:
        """Best-effort call to 2GIS public transport routing."""

        cache_key = self._cache_key("transit", {"start": start, "end": end})
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        request_body = {
            "points": [
                {"type": "stop", "lat": start[0], "lon": start[1]},
                {"type": "stop", "lat": end[0], "lon": end[1]},
            ],
            "transport": "public_transport",
            "route_mode": "fastest",
            "output": "detailed",
        }

        data = await self._request_post(
            self.PUBLIC_TRANSPORT_URL,
            params={},
            json_body=request_body,
            timeout=60,
        )

        if not data or "result" not in data:
            return None

        result = data["result"]
        if isinstance(result, list):
            result = result[0] if result else None

        if result:
            await self._set_cache(cache_key, result, ttl=settings.ROUTING_CACHE_TTL_SECONDS)
        return result

    async def get_distance_matrix(
        self,
        sources: List[Tuple[float, float]],
        targets: List[Tuple[float, float]],
        transport: str = "pedestrian",
    ) -> Optional[Dict[str, Any]]:
        if not sources or not targets:
            return None

        cache_key = self._cache_key(
            "distmatrix",
            {"sources": sources, "targets": targets, "transport": transport},
        )
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        request_body = {
            "points": [{"lat": lat, "lon": lon} for lat, lon in sources],
            "sources": list(range(len(sources))),
            "targets": list(range(len(targets))),
        }

        params = {"key": self.api_key, "version": "2.0"} if self.api_key else {"version": "2.0"}

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    self.DISTANCE_MATRIX_URL,
                    params=params,
                    json=request_body,
                )
            except httpx.TimeoutException as exc:  # pragma: no cover - network
                logger.error("2GIS distance matrix timeout")
                raise exc

        if response.status_code == 200:
            data = response.json()
            await self._set_cache(cache_key, data, ttl=settings.ROUTING_CACHE_TTL_SECONDS)
            return data

        if response.status_code == 429:
            logger.warning("2GIS distance matrix throttled")
            raise httpx.HTTPError("rate-limit")

        logger.error("2GIS distance matrix error %s: %s", response.status_code, response.text)
        return None

    def parse_distance_matrix(
        self, matrix_data: Dict[str, Any], num_sources: int, num_targets: int
    ) -> List[List[float]]:
        matrix = [[float("inf")] * num_targets for _ in range(num_sources)]
        for route in matrix_data.get("routes", []):
            s_idx = route.get("source_index", 0)
            t_idx = route.get("target_index", 0)
            if s_idx < num_sources and t_idx < num_targets:
                matrix[s_idx][t_idx] = route.get("distance", 0) / 1000.0
        return matrix

    def parse_geometry(self, route_data: Dict[str, Any]) -> List[Tuple[float, float]]:
        if not route_data:
            return []

        maneuvers = route_data.get("maneuvers", [])
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

        waypoints = route_data.get("waypoints", [])
        for waypoint in waypoints:
            point = waypoint.get("projected_point") or waypoint.get("original_point")
            if point and "lat" in point and "lon" in point:
                key = (round(point["lat"], 6), round(point["lon"], 6))
                if key not in seen:
                    seen.add(key)
                    collected.append((point["lat"], point["lon"]))

        return collected

    def parse_maneuvers(self, route_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        maneuvers: List[Dict[str, Any]] = []
        for maneuver in route_data.get("maneuvers", []):
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
                    "distance_m": float(distance) if distance is not None else 0.0,
                    "duration_s": float(duration) if duration is not None else 0.0,
                }
            )

        return maneuvers

    def parse_transit_route(self, route_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not route_data:
            return None

        # 2GIS returns result either as dict or list.
        if isinstance(route_data, list):
            route_data = route_data[0] if route_data else None
        if not isinstance(route_data, dict):
            return None

        duration_min = route_data.get("duration", 0) / 60.0
        distance_km = route_data.get("distance", 0) / 1000.0

        sections = (
            route_data.get("sections")
            or route_data.get("legs")
            or route_data.get("maneuvers", [])
        )

        boarding_stop: Optional[Dict[str, Any]] = None
        alighting_stop: Optional[Dict[str, Any]] = None
        line_name = ""
        vehicle_type = ""
        direction = ""
        vehicle_number = ""
        notes: List[str] = []

        for section in sections:
            if not isinstance(section, dict):
                continue

            section_type = section.get("type") or section.get("transport")

            transports = section.get("transports") or section.get("transport")
            if isinstance(transports, dict):
                transports = [transports]

            if isinstance(transports, list) and transports:
                transport = transports[0]
                line_name = transport.get("name") or transport.get("line_name") or line_name
                vehicle_type = (
                    transport.get("vehicle_type")
                    or transport.get("type")
                    or vehicle_type
                )
                direction = transport.get("direction") or direction
                vehicle_number = transport.get("vehicle_number") or vehicle_number
                if transport.get("description"):
                    notes.append(transport["description"])

            stops = section.get("stops") or section.get("stations") or []
            if stops and isinstance(stops, list):
                first = stops[0]
                last = stops[-1]
                boarding_stop = boarding_stop or {
                    "name": first.get("name", ""),
                    "lat": first.get("lat")
                    or first.get("point", {}).get("lat"),
                    "lon": first.get("lon")
                    or first.get("point", {}).get("lon"),
                    "side": first.get("side", ""),
                }
                alighting_stop = {
                    "name": last.get("name", ""),
                    "lat": last.get("lat")
                    or last.get("point", {}).get("lat"),
                    "lon": last.get("lon")
                    or last.get("point", {}).get("lon"),
                    "side": last.get("side", ""),
                }

            if isinstance(section_type, str) and "walk" in section_type:
                # Walk sections before/after transit – append textual note.
                walk_length = section.get("length") or section.get("distance")
                if walk_length:
                    notes.append(
                        f"Пешком {int(float(walk_length))} м"
                    )

        if not line_name and not vehicle_type:
            return None

        return {
            "duration_min": duration_min,
            "distance_km": distance_km,
            "line_name": line_name,
            "vehicle_type": vehicle_type,
            "direction": direction,
            "vehicle_number": vehicle_number,
            "boarding_stop": boarding_stop,
            "alighting_stop": alighting_stop,
            "notes": [note for note in notes if note],
        }

    # ------------------------------------------------------------------
    # Math helpers
    # ------------------------------------------------------------------

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import radians, sin, cos, sqrt, atan2

        r = 6371.0
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        dlon = radians(lon2 - lon1)
        dlat = radians(lat2 - lat1)

        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return r * c

    def _parse_wkt(self, wkt: str) -> List[Tuple[float, float]]:
        try:
            coords = wkt.replace("LINESTRING(", "").replace(")", "")
            result: List[Tuple[float, float]] = []
            for pair in coords.split(","):
                lon_str, lat_str = pair.strip().split()[:2]
                result.append((float(lat_str), float(lon_str)))
            return result
        except Exception:  # pragma: no cover - defensive
            logger.debug("Failed to parse WKT geometry: %s", wkt[:80])
            return []


twogis_client = TwoGISClient()
