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
    ORS_BASE_URL = "https://api.openrouteservice.org/v2/directions/foot-walking"
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.has_api_key = bool(settings.OPENROUTESERVICE_API_KEY)
        
        if not self.has_api_key:
            logger.warning(
                "OpenRouteService API key not configured. "
                "Using public endpoint with strict rate limits. "
                "Get your free key at https://openrouteservice.org/dev/#/signup"
            )
    
    async def connect_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
            logger.info("Routing service: Redis connected")
    
    def _get_cache_key(self, coordinates: List[Tuple[float, float]]) -> str:
        """Generate cache key from coordinates"""
        coords_str = json.dumps(coordinates, sort_keys=True)
        return f"route:{hashlib.sha256(coords_str.encode()).hexdigest()}"
    
    async def _get_cached_route(self, coordinates: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
        """Get cached route"""
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(coordinates)
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            logger.info(f"Route cache hit: {len(coordinates)} points")
            return json.loads(cached)
        
        return None
    
    async def _cache_route(self, coordinates: List[Tuple[float, float]], route_data: Dict[str, Any]) -> None:
        """Cache route data"""
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(coordinates)
        data = json.dumps(route_data)
        
        await self.redis_client.set(
            cache_key,
            data,
            ex=settings.ROUTING_CACHE_TTL_SECONDS
        )
        logger.info(f"Route cached: {len(coordinates)} points")
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True
    )
    async def _fetch_walking_route(
        self,
        coordinates: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        """Fetch walking route from OpenRouteService API with retry logic"""
        if len(coordinates) < 2:
            logger.warning("Need at least 2 coordinates for routing")
            return None
        
        if len(coordinates) > 50:
            logger.warning(f"Too many waypoints: {len(coordinates)}, limiting to 50")
            coordinates = coordinates[:50]
        
        coords_list = [[lon, lat] for lat, lon in coordinates]
        
        headers = {
            "Accept": "application/json, application/geo+json",
            "Content-Type": "application/json"
        }
        
        if self.has_api_key:
            headers["Authorization"] = settings.OPENROUTESERVICE_API_KEY
        
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
                    logger.info(f"Routing success: {len(coordinates)} points")
                    return data
                    
                elif response.status_code == 429:
                    logger.error("OpenRouteService rate limit exceeded")
                    if not self.has_api_key:
                        logger.error("Consider getting an API key: https://openrouteservice.org/dev/#/signup")
                    return None
                    
                else:
                    error_msg = f"Routing API error: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f" - {error_data.get('error', {}).get('message', '')}"
                    except:
                        pass
                    logger.error(error_msg)
                    return None
                    
            except httpx.TimeoutException:
                logger.error(f"Routing timeout for {len(coordinates)} points")
                raise
            except Exception as e:
                logger.error(f"Routing error: {str(e)}")
                raise
        
        return None
    
    async def get_walking_route(
        self,
        coordinates: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        """
        Get walking route through multiple points using real roads with caching
        
        Args:
            coordinates: List of (lat, lon) tuples
            
        Returns:
            Route data from OpenRouteService or None if failed
        """
        if len(coordinates) < 2:
            return None
        
        cached = await self._get_cached_route(coordinates)
        if cached:
            return cached
        
        route_data = await self._fetch_walking_route(coordinates)
        
        if route_data:
            await self._cache_route(coordinates, route_data)
        
        return route_data
    
    async def calculate_route_geometry(
        self,
        start: Tuple[float, float],
        waypoints: List[Tuple[float, float]]
    ) -> List[List[float]]:
        """
        Calculate route geometry for display on map
        
        Args:
            start: Starting point (lat, lon)
            waypoints: List of waypoints (lat, lon)
            
        Returns:
            List of [lat, lon] coordinates forming the route
        """
        all_coords = [start] + waypoints
        
        route = await self.get_walking_route(all_coords)
        
        if route and "routes" in route and len(route["routes"]) > 0:
            geometry = route["routes"][0]["geometry"]["coordinates"]
            result = [[coord[1], coord[0]] for coord in geometry]
            logger.info(f"Route geometry: {len(result)} points")
            return result
        
        logger.warning("Routing failed, using straight lines as fallback")
        return [[lat, lon] for lat, lon in all_coords]
    
    async def get_route_distance(
        self,
        start: Tuple[float, float],
        waypoints: List[Tuple[float, float]]
    ) -> float:
        """
        Get total route distance in kilometers
        
        Returns:
            Distance in km or estimated distance if routing fails
        """
        all_coords = [start] + waypoints
        route = await self.get_walking_route(all_coords)
        
        if route and "routes" in route and len(route["routes"]) > 0:
            distance_meters = route["routes"][0]["summary"]["distance"]
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