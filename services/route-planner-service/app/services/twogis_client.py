import hashlib
import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
import redis.asyncio as redis
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class TransportType(str, Enum):
    WALKING = "pedestrian"
    DRIVING = "car"
    BICYCLE = "bicycle"


class TwoGISClient:
    PLACES_URL = "https://catalog.api.2gis.com/3.0/items"
    GEOCODER_URL = "https://catalog.api.2gis.com/3.0/items/geocode"
    ROUTING_URL = "https://routing.api.2gis.com/routing/7.0.0/global"
    DISTANCE_MATRIX_URL = "https://routing.api.2gis.com/get_dist_matrix"
    RUBRICS_URL = "https://catalog.api.2gis.com/2.0/catalog/rubric/search"

    NIZHNY_NOVGOROD_REGION_ID = 52

    CAFE_RUBRIC_ID = 162
    RESTAURANT_RUBRIC_ID = 164
    BAR_RUBRIC_ID = 159

    def __init__(self) -> None:
        self.api_key = settings.TWOGIS_API_KEY
        self.redis_client: Optional[redis.Redis] = None

        if not self.api_key:
            logger.warning("2GIS API key not configured")

    async def connect_redis(self) -> None:
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
            logger.info("2GIS client: Redis connected")

    def _cache_key(self, prefix: str, params: Dict) -> str:
        key_str = json.dumps(params, sort_keys=True)
        hash_val = hashlib.sha256(key_str.encode()).hexdigest()
        return f"2gis:{prefix}:{hash_val}"

    async def _get_cached(self, key: str) -> Optional[Any]:
        if not self.redis_client:
            await self.connect_redis()

        cached = await self.redis_client.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def _set_cache(self, key: str, data: Any, ttl: int = 3600) -> None:
        if not self.redis_client:
            await self.connect_redis()

        await self.redis_client.set(key, json.dumps(data), ex=ttl)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _request_get(
        self, url: str, params: Dict[str, Any], timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("2GIS API key not configured")
            return None

        params = {**params, "key": self.api_key}

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    return response.json()
                if response.status_code == 400:
                    logger.error("2GIS API 400: %s", response.text)
                    return None
                if response.status_code == 429:
                    logger.warning("2GIS rate limit exceeded")
                    raise httpx.HTTPError("Rate limit")

                logger.error(
                    "2GIS API error: %s - %s", response.status_code, response.text
                )
                return None
            except httpx.TimeoutException:
                logger.error("2GIS request timeout: %s", url)
                raise
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("2GIS request failed: %s", exc)
                raise

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
        timeout: int = 60,
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("2GIS API key not configured")
            return None

        params = {**params, "key": self.api_key}

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    url,
                    params=params,
                    json=json_body,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    return response.json()
                if response.status_code == 400:
                    logger.error("2GIS API 400: %s", response.text)
                    return None
                if response.status_code == 429:
                    logger.warning("2GIS rate limit exceeded")
                    raise httpx.HTTPError("Rate limit")

                logger.error(
                    "2GIS API error: %s - %s", response.status_code, response.text
                )
                return None
            except httpx.TimeoutException:
                logger.error("2GIS request timeout: %s", url)
                raise
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("2GIS request failed: %s", exc)
                raise

    async def geocode(
        self, query: str, location: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
        cache_key = self._cache_key("geocode", {"q": query})
        cached = await self._get_cached(cache_key)
        if cached:
            return tuple(cached)

        coords = await self._geocode_places(query, location)
        if not coords:
            coords = await self._geocode_address(query, location)

        if coords:
            await self._set_cache(cache_key, coords, ttl=86400)
            logger.info("✓ Geocoded: %s → %s", query, coords)
            return coords

        return None

    async def _geocode_places(
        self, query: str, location: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
        params: Dict[str, Any] = {
            "q": f"{query}, Нижний Новгород",
            "fields": "items.point,items.address",
            "page_size": 1,
        }

        if location:
            params["location"] = f"{location[1]},{location[0]}"
            params["sort_point"] = f"{location[1]},{location[0]}"

        data = await self._request_get(self.PLACES_URL, params)

        if data and data.get("result", {}).get("items"):
            point = data["result"]["items"][0].get("point")
            if point and {"lat", "lon"} <= set(point):
                return (point["lat"], point["lon"])
        return None

    async def _geocode_address(
        self, query: str, location: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
        params: Dict[str, Any] = {
            "q": f"{query}, Нижний Новгород",
            "region_id": self.NIZHNY_NOVGOROD_REGION_ID,
            "fields": "items.point",
            "page_size": 1,
        }

        if location:
            params["location"] = f"{location[1]},{location[0]}"

        data = await self._request_get(self.GEOCODER_URL, params)

        if data and data.get("result", {}).get("items"):
            point = data["result"]["items"][0].get("point")
            if point and {"lat", "lon"} <= set(point):
                return (point["lat"], point["lon"])
        return None

    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        params = {
            "lon": lon,
            "lat": lat,
            "region_id": self.NIZHNY_NOVGOROD_REGION_ID,
            "fields": "items.full_name",
            "page_size": 1,
        }

        data = await self._request_get(self.GEOCODER_URL, params)

        if data and data.get("result", {}).get("items"):
            return data["result"]["items"][0].get("full_name", "")
        return None

    async def get_walking_route(
        self, points: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        if len(points) < 2:
            return None

        if len(points) > 10:
            logger.warning("Too many waypoints: %s, sampling to 10", len(points))
            indices = [0]
            step = (len(points) - 2) / 8
            for i in range(1, 9):
                idx = int(1 + i * step)
                if idx < len(points) - 1:
                    indices.append(idx)
            indices.append(len(points) - 1)
            indices = sorted(set(indices))
            points = [points[i] for i in indices]
            logger.info("Sampled route to %s waypoints: indices %s", len(points), indices)

        cache_key = self._cache_key("route_walk", {"points": points})
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        formatted_points = []
        for index, (lat, lon) in enumerate(points):
            point_type = "walking" if index == 0 else "stop" if index == len(points) - 1 else "pref"
            formatted_points.append({"type": point_type, "lon": lon, "lat": lat})

        request_body = {
            "points": formatted_points,
            "transport": "pedestrian",
            "route_mode": "fastest",
            "output": "detailed",
        }

        data = await self._request_post(self.ROUTING_URL, params={}, json_body=request_body, timeout=60)

        if data and "result" in data:
            result = data["result"]
            if isinstance(result, list) and result:
                result = result[0]

            await self._set_cache(cache_key, result, ttl=3600)

            distance_km = result.get("distance", 0) / 1000
            duration_min = result.get("duration", 0) / 60
            logger.info("✓ Walking route: %.2fkm, %.1fmin", distance_km, duration_min)
            return result
        return None

    async def get_distance_matrix(
        self,
        sources: List[Tuple[float, float]],
        targets: List[Tuple[float, float]],
        transport: str = "pedestrian",
    ) -> Optional[Dict[str, Any]]:
        if not sources or not targets:
            return None

        if len(sources) > 25 or len(targets) > 25:
            logger.warning(
                "Too many points: %s×%s, truncating", len(sources), len(targets)
            )
            sources = sources[:25]
            targets = targets[:25]

        cache_key = self._cache_key(
            "distmatrix", {"sources": sources, "targets": targets, "transport": transport}
        )
        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        formatted_points = [{"lat": lat, "lon": lon} for lat, lon in sources]

        request_body = {
            "points": formatted_points,
            "sources": list(range(len(sources))),
            "targets": list(range(len(targets))),
        }

        data = await self._request_post(
            self.DISTANCE_MATRIX_URL,
            params={"version": "2.0"},
            json_body=request_body,
            timeout=30,
        )

        if data and "routes" in data:
            await self._set_cache(cache_key, data, ttl=3600)
            logger.info("✓ Distance matrix: %s×%s", len(sources), len(targets))
            return data
        return None

    def parse_distance_matrix(
        self, matrix_data: Dict[str, Any], num_sources: int, num_targets: int
    ) -> List[List[float]]:
        routes = matrix_data.get("routes", [])
        matrix = [[float("inf")] * num_targets for _ in range(num_sources)]

        for route in routes:
            src = route.get("source_index", 0)
            tgt = route.get("target_index", 0)
            dist_m = route.get("distance", 0)

            if src < num_sources and tgt < num_targets:
                matrix[src][tgt] = dist_m / 1000.0
        return matrix

    def parse_geometry(self, route_data: Dict[str, Any]) -> List[Tuple[float, float]]:
        if not route_data:
            return []

        maneuvers = route_data.get("maneuvers", [])
        if maneuvers:
            all_points: List[Tuple[float, float]] = []
            for maneuver in maneuvers:
                if not isinstance(maneuver, dict):
                    continue
                geometry_segments = maneuver.get("outcoming_path", {}).get("geometry", [])
                for segment in geometry_segments:
                    if not isinstance(segment, dict):
                        continue
                    selection = segment.get("selection", "")
                    if selection.startswith("LINESTRING"):
                        points = self._parse_wkt_linestring(selection)
                        all_points.extend(points)

            if all_points:
                unique_points: List[Tuple[float, float]] = []
                seen = set()
                for lat, lon in all_points:
                    key = (round(lat, 6), round(lon, 6))
                    if key not in seen:
                        seen.add(key)
                        unique_points.append((lat, lon))
                logger.info(
                    "✓ Parsed %s unique points from %s maneuvers",
                    len(unique_points),
                    len(maneuvers),
                )
                return unique_points
            logger.warning(
                "Found %s maneuvers but no geometry points extracted", len(maneuvers)
            )

        waypoints = route_data.get("waypoints", [])
        if waypoints:
            points: List[Tuple[float, float]] = []
            for waypoint in waypoints:
                if not isinstance(waypoint, dict):
                    continue
                projected = waypoint.get("projected_point") or waypoint.get("original_point", {})
                if {"lat", "lon"} <= set(projected):
                    points.append((projected["lat"], projected["lon"]))

            if points:
                logger.info("✓ Parsed %s points from waypoints (fallback)", len(points))
                return points

        logger.error("Could not parse geometry. Available keys: %s", list(route_data.keys()))
        return []

    def _parse_wkt_linestring(self, wkt: str) -> List[Tuple[float, float]]:
        try:
            coords_str = wkt.replace("LINESTRING(", "").rstrip(")").strip()
            if not coords_str:
                return []

            points: List[Tuple[float, float]] = []
            for pair in coords_str.split(","):
                parts = pair.strip().split()
                if len(parts) >= 2:
                    lon, lat = map(float, parts[:2])
                    points.append((lat, lon))

            if not points:
                logger.warning("No points extracted from WKT: %s", wkt[:100])
            return points
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to parse WKT LINESTRING: %s", exc)
            return []

    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import atan2, cos, radians, sin, sqrt

        r_earth = 6371.0
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return r_earth * c


twogis_client = TwoGISClient()
