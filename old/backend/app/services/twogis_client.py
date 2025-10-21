import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple
from enum import Enum

import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
    
    def __init__(self):
        self.api_key = settings.TWOGIS_API_KEY
        self.redis_client: Optional[redis.Redis] = None
        
        if not self.api_key:
            logger.warning("2GIS API key not configured")
    
    async def connect_redis(self):
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
    
    async def _set_cache(self, key: str, data: Any, ttl: int = 3600):
        if not self.redis_client:
            await self.connect_redis()
        
        await self.redis_client.set(key, json.dumps(data), ex=ttl)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def _request_get(
        self,
        url: str,
        params: Dict[str, Any],
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("2GIS API key not configured")
            return None
        
        params["key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 400:
                    logger.error(f"2GIS API 400: {response.text}")
                    return None
                elif response.status_code == 429:
                    logger.warning("2GIS rate limit exceeded")
                    raise httpx.HTTPError("Rate limit")
                else:
                    logger.error(f"2GIS API error: {response.status_code} - {response.text}")
                    return None
                    
            except httpx.TimeoutException:
                logger.error(f"2GIS request timeout: {url}")
                raise
            except Exception as e:
                logger.error(f"2GIS request failed: {e}")
                raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    async def _request_post(
        self,
        url: str,
        params: Dict[str, Any],
        json_body: Dict[str, Any],
        timeout: int = 60
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            logger.error("2GIS API key not configured")
            return None
        
        params["key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    url,
                    params=params,
                    json=json_body,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 400:
                    logger.error(f"2GIS API 400: {response.text}")
                    return None
                elif response.status_code == 429:
                    logger.warning("2GIS rate limit exceeded")
                    raise httpx.HTTPError("Rate limit")
                else:
                    logger.error(f"2GIS API error: {response.status_code} - {response.text}")
                    return None
                    
            except httpx.TimeoutException:
                logger.error(f"2GIS request timeout: {url}")
                raise
            except Exception as e:
                logger.error(f"2GIS request failed: {e}")
                raise
    
    async def geocode(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None
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
            logger.info(f"✓ Geocoded: {query} → {coords}")
            return coords
        
        return None
    
    async def _geocode_places(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
        params = {
            "q": f"{query}, Нижний Новгород",
            "fields": "items.point,items.address",
            "page_size": 1
        }
        
        if location:
            params["location"] = f"{location[1]},{location[0]}"
            params["sort_point"] = f"{location[1]},{location[0]}"
        
        data = await self._request_get(self.PLACES_URL, params)
        
        if data and "result" in data and "items" in data["result"]:
            items = data["result"]["items"]
            if items and "point" in items[0]:
                point = items[0]["point"]
                return (point["lat"], point["lon"])
        
        return None
    
    async def _geocode_address(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
        params = {
            "q": f"{query}, Нижний Новгород",
            "region_id": self.NIZHNY_NOVGOROD_REGION_ID,
            "fields": "items.point",
            "page_size": 1
        }
        
        if location:
            params["location"] = f"{location[1]},{location[0]}"
        
        data = await self._request_get(self.GEOCODER_URL, params)
        
        if data and "result" in data and "items" in data["result"]:
            items = data["result"]["items"]
            if items and "point" in items[0]:
                point = items[0]["point"]
                return (point["lat"], point["lon"])
        
        return None
    
    async def reverse_geocode(
        self,
        lat: float,
        lon: float
    ) -> Optional[str]:
        params = {
            "lon": lon,
            "lat": lat,
            "region_id": self.NIZHNY_NOVGOROD_REGION_ID,
            "fields": "items.full_name",
            "page_size": 1
        }
        
        data = await self._request_get(self.GEOCODER_URL, params)
        
        if data and "result" in data and "items" in data["result"]:
            items = data["result"]["items"]
            if items:
                return items[0].get("full_name", "")
        
        return None
    
    async def get_walking_route(
        self,
        points: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        if len(points) < 2:
            return None
        
        # 2GIS Routing API free tier supports up to 10 waypoints
        if len(points) > 10:
            logger.warning(f"Too many waypoints: {len(points)}, sampling to 10")
            indices = [0]  # Start
            
            # Add evenly spaced intermediate points
            step = (len(points) - 2) / 8  # 8 intermediate points
            for i in range(1, 9):
                idx = int(1 + i * step)
                if idx < len(points) - 1:
                    indices.append(idx)
            
            indices.append(len(points) - 1)  # End
            indices = sorted(set(indices))
            points = [points[i] for i in indices]
            logger.info(f"Sampled route to {len(points)} waypoints: indices {indices}")
        
        cache_key = self._cache_key("route_walk", {"points": points})
        cached = await self._get_cached(cache_key)
        if cached:
            return cached
        
        formatted_points = []
        for i, (lat, lon) in enumerate(points):
            point_type = "walking" if i == 0 else "stop" if i == len(points)-1 else "pref"
            formatted_points.append({
                "type": point_type,
                "lon": lon,
                "lat": lat
            })
        
        request_body = {
            "points": formatted_points,
            "transport": "pedestrian",
            "route_mode": "fastest",
            "output": "detailed"
        }
        
        data = await self._request_post(
            self.ROUTING_URL,
            params={},
            json_body=request_body,
            timeout=60
        )
        
        if data and "result" in data:
            result = data["result"]
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            await self._set_cache(cache_key, result, ttl=3600)
            
            distance_km = result.get("distance", 0) / 1000
            duration_min = result.get("duration", 0) / 60
            logger.info(f"✓ Walking route: {distance_km:.2f}km, {duration_min:.1f}min")
            
            return result
        
        return None
    
    async def request_distance_matrix(
        self,
        points: Sequence[Tuple[float, float]],
        source_indices: Sequence[int],
        target_indices: Sequence[int],
        transport: str = "pedestrian",
    ) -> Optional[Dict[str, Any]]:
        if not points or not source_indices or not target_indices:
            return None

        serialized_points = [{"lat": lat, "lon": lon} for lat, lon in points]

        cache_key = self._cache_key(
            "distmatrix",
            {
                "points": serialized_points,
                "sources": list(source_indices),
                "targets": list(target_indices),
                "transport": transport,
            },
        )

        cached = await self._get_cached(cache_key)
        if cached:
            return cached

        request_body = {
            "points": serialized_points,
            "sources": list(source_indices),
            "targets": list(target_indices),
        }

        data = await self._request_post(
            self.DISTANCE_MATRIX_URL,
            params={"version": "2.0"},
            json_body=request_body,
            timeout=30,
        )

        if not data or "routes" not in data:
            return None

        await self._set_cache(cache_key, data, ttl=3600)
        logger.info(
            "✓ Distance matrix chunk: %s×%s",
            len(source_indices),
            len(target_indices),
        )
        return data

    async def get_distance_matrix(
        self,
        sources: Sequence[Tuple[float, float]],
        targets: Sequence[Tuple[float, float]],
        transport: str = "pedestrian",
    ) -> Optional[Dict[str, Any]]:
        if not sources or not targets:
            return None

        unique_points: List[Tuple[float, float]] = []
        point_to_index: Dict[Tuple[float, float], int] = {}

        def ensure_point(point: Tuple[float, float]) -> int:
            idx = point_to_index.get(point)
            if idx is None:
                idx = len(unique_points)
                unique_points.append(point)
                point_to_index[point] = idx
            return idx

        source_indices = [ensure_point(pt) for pt in sources]
        target_indices = [ensure_point(pt) for pt in targets]

        return await self.request_distance_matrix(
            unique_points,
            source_indices,
            target_indices,
            transport=transport,
        )
    
    def parse_distance_matrix(
        self,
        matrix_data: Dict[str, Any],
        num_sources: int,
        num_targets: int
    ) -> List[List[float]]:
        routes = matrix_data.get("routes", [])
        matrix = [[float('inf')] * num_targets for _ in range(num_sources)]
        
        for route in routes:
            src = route.get("source_index", 0)
            tgt = route.get("target_index", 0)
            dist_m = route.get("distance", 0)
            
            if src < num_sources and tgt < num_targets:
                matrix[src][tgt] = dist_m / 1000.0
        
        return matrix
    
    async def search_cafes(
        self,
        location: Tuple[float, float],
        radius_km: float = 1.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        cache_key = self._cache_key("cafes", {"loc": location, "r": radius_km})
        cached = await self._get_cached(cache_key)
        if cached:
            return cached
        
        radius_m = int(radius_km * 1000)
        
        params = {
            "rubric_id": f"{self.CAFE_RUBRIC_ID},{self.RESTAURANT_RUBRIC_ID}",
            "point": f"{location[1]},{location[0]}",
            "radius": radius_m,
            "sort": "rating",
            "fields": "items.point,items.address_name,items.schedule,items.contact_groups,items.rubrics",
            "page_size": min(limit, 10)
        }
        
        data = await self._request_get(self.PLACES_URL, params)
        
        cafes = []
        if data and "result" in data and "items" in data["result"]:
            items = data["result"]["items"]
            
            for item in items:
                point = item.get("point", {})
                if not point or "lat" not in point:
                    continue
                
                parsed = {
                    "id": str(item.get("id", "")),
                    "name": item.get("name", "Кафе"),
                    "lat": point.get("lat"),
                    "lon": point.get("lon"),
                    "address": item.get("address_name", ""),
                    "rubrics": [r.get("name", "") for r in item.get("rubrics", [])],
                    "schedule": item.get("schedule", {}),
                }
                
                contact_groups = item.get("contact_groups", [])
                if contact_groups:
                    contacts = contact_groups[0].get("contacts", [])
                    for contact in contacts:
                        if contact.get("type") == "phone":
                            parsed["phone"] = contact.get("text")
                        elif contact.get("type") == "website":
                            parsed["website"] = contact.get("url")
                
                cafes.append(parsed)
            
            if cafes:
                await self._set_cache(cache_key, cafes, ttl=3600)
                logger.info(f"✓ Found {len(cafes)} cafes near {location}")
        
        return cafes
    
    def parse_geometry(self, route_data: Dict[str, Any]) -> List[Tuple[float, float]]:
        if not route_data:
            return []
        
        # Method 1: Parse from maneuvers[].outcoming_path.geometry[].selection (WKT format)
        maneuvers = route_data.get("maneuvers", [])
        if maneuvers:
            all_points = []
            segments_parsed = 0
            
            for maneuver_idx, maneuver in enumerate(maneuvers):
                if not isinstance(maneuver, dict):
                    continue
                
                outcoming_path = maneuver.get("outcoming_path", {})
                geometry_segments = outcoming_path.get("geometry", [])
                
                for seg_idx, segment in enumerate(geometry_segments):
                    if not isinstance(segment, dict):
                        continue
                    
                    # Parse WKT LINESTRING from 'selection'
                    selection = segment.get("selection", "")
                    if selection.startswith("LINESTRING"):
                        points = self._parse_wkt_linestring(selection)
                        if points:
                            all_points.extend(points)
                            segments_parsed += 1
            
            if all_points:
                # Remove duplicates while preserving order
                unique_points = []
                seen = set()
                for p in all_points:
                    # Round to 6 decimal places for deduplication
                    key = (round(p[0], 6), round(p[1], 6))
                    if key not in seen:
                        seen.add(key)
                        unique_points.append(p)
                
                logger.info(f"✓ Parsed {len(unique_points)} unique points from {segments_parsed} WKT segments across {len(maneuvers)} maneuvers")
                return unique_points
            else:
                logger.warning(f"Found {len(maneuvers)} maneuvers but no geometry points extracted")
        
        # Method 2: Try waypoints (fallback)
        waypoints = route_data.get("waypoints", [])
        if waypoints:
            points = []
            for wp in waypoints:
                if isinstance(wp, dict):
                    proj = wp.get("projected_point", wp.get("original_point", {}))
                    if "lat" in proj and "lon" in proj:
                        points.append((proj["lat"], proj["lon"]))
            
            if points:
                logger.info(f"✓ Parsed {len(points)} points from waypoints (fallback)")
                return points
        
        logger.error(f"Could not parse geometry. Available keys: {list(route_data.keys())}")
        return []
    
    def _parse_wkt_linestring(self, wkt: str) -> List[Tuple[float, float]]:
        """Parse WKT LINESTRING format: 'LINESTRING(lon1 lat1, lon2 lat2, ...)'"""
        try:
            # Remove 'LINESTRING(' and ')'
            coords_str = wkt.replace("LINESTRING(", "").replace(")", "").strip()
            
            points = []
            for pair in coords_str.split(","):
                pair = pair.strip()
                if not pair:
                    continue
                
                parts = pair.split()
                if len(parts) >= 2:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    points.append((lat, lon))
            
            if not points:
                logger.warning(f"No points extracted from WKT: {wkt[:100]}...")
            
            return points
            
        except Exception as e:
            logger.error(f"Failed to parse WKT LINESTRING: {e}, WKT: {wkt[:100]}...")
            return []
    
    def calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371.0
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        dlon = radians(lon2 - lon1)
        dlat = radians(lat2 - lat1)
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c


twogis_client = TwoGISClient()