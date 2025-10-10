import hashlib
import json
import logging
from typing import List, Tuple, Optional, Dict, Any
import httpx
import numpy as np
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)


class RoutingService:
    OSRM_BASE_URL = "https://router.project-osrm.org"
    
    ORS_BASE_URL = "https://api.openrouteservice.org/v2/directions/foot-walking"
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.has_ors_key = bool(settings.OPENROUTESERVICE_API_KEY)
        
        self.primary_service = "osrm"
        
        logger.info(f"Routing service initialized: primary={self.primary_service}")
        if self.has_ors_key:
            logger.info("OpenRouteService API key detected, will use as fallback")
    
    async def connect_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
            logger.info("Routing service: Redis connected")
    
    def _get_cache_key(self, coordinates: List[Tuple[float, float]]) -> str:
        coords_str = json.dumps(coordinates, sort_keys=True)
        return f"route:{hashlib.sha256(coords_str.encode()).hexdigest()}"
    
    async def _get_cached_route(self, coordinates: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(coordinates)
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            logger.info(f"✓ Route cache hit: {len(coordinates)} points")
            return json.loads(cached)
        
        return None
    
    async def _cache_route(self, coordinates: List[Tuple[float, float]], route_data: Dict[str, Any]) -> None:
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(coordinates)
        data = json.dumps(route_data)
        
        await self.redis_client.set(
            cache_key,
            data,
            ex=settings.ROUTING_CACHE_TTL_SECONDS
        )
        logger.info(f"✓ Route cached: {len(coordinates)} points")
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True
    )
    async def _fetch_osrm_route(
        self,
        coordinates: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        if len(coordinates) < 2:
            return None
        
        # OSRM формат: lon,lat;lon,lat;...
        coords_str = ";".join([f"{lon},{lat}" for lat, lon in coordinates])
        
        url = f"{self.OSRM_BASE_URL}/route/v1/foot/{coords_str}"
        
        params = {
            "overview": "full",  
            "geometries": "geojson",  
            "steps": False,
            "alternatives": False,
        }
        
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            try:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("code") == "Ok" and data.get("routes"):
                        route = data["routes"][0]
                        logger.info(
                            f"✓ OSRM route: {len(coordinates)} waypoints, "
                            f"{route['distance']/1000:.2f}km, "
                            f"{route['duration']/60:.1f}min"
                        )
                        return data
                    else:
                        logger.error(f"OSRM error: {data.get('code')} - {data.get('message')}")
                        return None
                else:
                    logger.error(f"OSRM HTTP error: {response.status_code}")
                    return None
                    
            except httpx.TimeoutException:
                logger.error(f"OSRM timeout for {len(coordinates)} points")
                raise
            except Exception as e:
                logger.error(f"OSRM error: {str(e)}")
                raise
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True
    )
    async def _fetch_ors_route(
        self,
        coordinates: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        if not self.has_ors_key:
            return None
        
        if len(coordinates) < 2:
            return None
        
        coords_list = [[lon, lat] for lat, lon in coordinates]
        
        headers = {
            "Accept": "application/json, application/geo+json",
            "Content-Type": "application/json",
            "Authorization": settings.OPENROUTESERVICE_API_KEY
        }
        
        payload = {
            "coordinates": coords_list,
            "language": "ru",
            "instructions": False,
            "elevation": False
        }
        
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            try:
                response = await client.post(
                    self.ORS_BASE_URL,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✓ ORS route: {len(coordinates)} waypoints")
                    return data
                else:
                    logger.error(f"ORS error: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"ORS error: {str(e)}")
                raise
    
    async def get_walking_route(
        self,
        coordinates: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        if len(coordinates) < 2:
            return None
        
        if len(coordinates) > 25:
            logger.warning(f"Too many waypoints: {len(coordinates)}, sampling to 25")
            indices = [0] + list(np.linspace(1, len(coordinates)-2, 23, dtype=int)) + [len(coordinates)-1]
            coordinates = [coordinates[i] for i in sorted(set(indices))]
        
        cached = await self._get_cached_route(coordinates)
        if cached:
            return cached
        
        try:
            logger.info(f"Requesting OSRM route for {len(coordinates)} points...")
            route_data = await self._fetch_osrm_route(coordinates)
            
            if route_data:
                await self._cache_route(coordinates, route_data)
                return route_data
        except Exception as e:
            logger.error(f"OSRM failed: {str(e)}")
        
        # Fallback на ORS если есть ключ
        if self.has_ors_key:
            try:
                logger.info(f"Falling back to ORS for {len(coordinates)} points...")
                route_data = await self._fetch_ors_route(coordinates)
                
                if route_data:
                    await self._cache_route(coordinates, route_data)
                    return route_data
            except Exception as e:
                logger.error(f"ORS fallback failed: {str(e)}")
        
        logger.warning("All routing services failed, will use straight lines")
        return None
    
    async def calculate_route_geometry(
        self,
        start: Tuple[float, float],
        waypoints: List[Tuple[float, float]]
    ) -> List[List[float]]:
        all_coords = [start] + waypoints
        
        route = await self.get_walking_route(all_coords)
        
        if route and "routes" in route and len(route["routes"]) > 0:
            geometry = route["routes"][0].get("geometry")
            
            if geometry and "coordinates" in geometry:
                coords = geometry["coordinates"]
                result = [[coord[1], coord[0]] for coord in coords]
                
                validated = self._validate_and_fix_geometry(result, all_coords)
                logger.info(f"✓ Geometry: {len(validated)} points")
                return validated
        
        logger.warning("⚠ Fallback to straight lines")
        return [[lat, lon] for lat, lon in all_coords]
    
    def _validate_and_fix_geometry(
        self,
        geometry: List[List[float]],
        waypoints: List[Tuple[float, float]]
    ) -> List[List[float]]:
        if not geometry or len(geometry) < 2:
            return [[lat, lon] for lat, lon in waypoints]
        
        fixed = []
        waypoint_idx = 0
        tolerance = 0.001
        
        for i, point in enumerate(geometry):
            fixed.append(point)
            
            if waypoint_idx < len(waypoints):
                wp_lat, wp_lon = waypoints[waypoint_idx]
                dist = abs(point[0] - wp_lat) + abs(point[1] - wp_lon)
                
                if dist < tolerance:
                    waypoint_idx += 1
                elif i == len(geometry) - 1 and waypoint_idx < len(waypoints):
                    for remaining_wp in waypoints[waypoint_idx:]:
                        fixed.append([remaining_wp[0], remaining_wp[1]])
                    break
        
        if len(fixed) < len(waypoints):
            logger.warning(f"Geometry incomplete, adding {len(waypoints) - len(fixed)} missing waypoints")
            for wp in waypoints[len(fixed):]:
                fixed.append([wp[0], wp[1]])
        
        return fixed
    
    async def get_route_distance(
        self,
        start: Tuple[float, float],
        waypoints: List[Tuple[float, float]]
    ) -> float:
        all_coords = [start] + waypoints
        route = await self.get_walking_route(all_coords)
        
        if route and "routes" in route and len(route["routes"]) > 0:
            distance_meters = route["routes"][0].get("distance", 0)
            return distance_meters / 1000.0
        
        total = 0.0
        for i in range(len(all_coords) - 1):
            total += self.calculate_distance_km(
                all_coords[i][0], all_coords[i][1],
                all_coords[i+1][0], all_coords[i+1][1]
            )
        return total
    
    def calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance calculation"""
        R = 6371.0
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlon = np.radians(lon2 - lon1)
        dlat = np.radians(lat2 - lat1)
        
        a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c
    
    async def clear_cache(self) -> int:
        """Clear all routing cache. Returns number of keys deleted."""
        if not self.redis_client:
            await self.connect_redis()
        
        cursor = 0
        deleted = 0
        
        while True:
            cursor, keys = await self.redis_client.scan(cursor, match="route:*", count=100)
            if keys:
                deleted += await self.redis_client.delete(*keys)
            if cursor == 0:
                break
        
        logger.info(f"Cleared {deleted} routing cache entries")
        return deleted


routing_service = RoutingService()