import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class TransportType(str, Enum):
    WALKING = "pedestrian"
    DRIVING = "car"
    TRANSIT = "transit"


class TwoGISClient:
    """Unified client for all 2GIS APIs with caching and error handling"""
    
    GEOCODER_URL = "https://catalog.api.2gis.com/3.0/items/geocode"
    DIRECTIONS_URL = "https://routing.api.2gis.com/get_dist_matrix"
    ROUTING_URL = "https://routing.api.2gis.com/get_route"
    PLACES_URL = "https://catalog.api.2gis.com/3.0/items"
    SUGGEST_URL = "https://catalog.api.2gis.com/3.0/suggests"
    TRANSIT_URL = "https://public-transport.api.2gis.com/routing"
    
    NIZHNY_NOVGOROD_REGION_ID = 97
    
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
    )
    async def _request(
        self,
        url: str,
        params: Dict[str, Any],
        timeout: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated request to 2GIS API"""
        
        if not self.api_key:
            logger.error("2GIS API key not configured")
            return None
        
        params["key"] = self.api_key
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning("2GIS rate limit exceeded")
                    raise httpx.HTTPError("Rate limit")
                else:
                    logger.error(f"2GIS API error: {response.status_code}")
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
        """Geocode address to coordinates using 2GIS Geocoder API"""
        
        cache_key = self._cache_key("geocode", {"q": query})
        cached = await self._get_cached(cache_key)
        if cached:
            return tuple(cached)
        
        params = {
            "q": f"{query}, Нижний Новгород",
            "region_id": self.NIZHNY_NOVGOROD_REGION_ID,
            "fields": "items.point",
            "page_size": 1
        }
        
        if location:
            params["location"] = f"{location[1]},{location[0]}"
        
        data = await self._request(self.GEOCODER_URL, params)
        
        if data and "result" in data and "items" in data["result"]:
            items = data["result"]["items"]
            if items and "point" in items[0]:
                point = items[0]["point"]
                coords = (point["lat"], point["lon"])
                await self._set_cache(cache_key, coords, ttl=86400)
                logger.info(f"✓ Geocoded: {query} → {coords}")
                return coords
        
        return None
    
    async def reverse_geocode(
        self,
        lat: float,
        lon: float
    ) -> Optional[str]:
        """Reverse geocode coordinates to address"""
        
        params = {
            "lon": lon,
            "lat": lat,
            "region_id": self.NIZHNY_NOVGOROD_REGION_ID,
            "fields": "items.full_name",
            "page_size": 1
        }
        
        data = await self._request(self.GEOCODER_URL, params)
        
        if data and "result" in data and "items" in data["result"]:
            items = data["result"]["items"]
            if items:
                return items[0].get("full_name", "")
        
        return None
    
    async def get_walking_route(
        self,
        points: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        """Get detailed walking route - 2GIS supports max 10 waypoints"""
        
        if len(points) < 2:
            return None
        
        # 2GIS Routing API limit: 10 waypoints max
        if len(points) > 10:
            logger.warning(f"Too many waypoints: {len(points)}, sampling to 10")
            # Keep first, last, and sample middle points
            indices = [0] + list(range(1, len(points)-1, max(1, (len(points)-2)//8))) + [len(points)-1]
            indices = sorted(set(indices))[:10]
            points = [points[i] for i in indices]
        
        cache_key = self._cache_key("route_walk", {"points": points})
        cached = await self._get_cached(cache_key)
        if cached:
            return cached
        
        # Format as array of objects
        formatted_points = [{"lat": lat, "lon": lon} for lat, lon in points]
        
        params = {
            "points": json.dumps(formatted_points),
            "type": TransportType.WALKING.value,
            "output": "summary,geometry",
        }
        
        data = await self._request(self.ROUTING_URL, params, timeout=60)
        
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
    
    async def get_transit_route(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> Optional[Dict[str, Any]]:
        """Get public transit route - NOT IMPLEMENTED for 2GIS free tier"""
        # 2GIS Public Transport API requires special access
        # For now, return None to skip transit suggestions
        logger.info("Transit API not available in current 2GIS plan")
        return None
    
    async def search_places(
        self,
        query: str,
        location: Tuple[float, float],
        radius: int = 1000,
        rubric_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for places using 2GIS Places API"""
        
        cache_key = self._cache_key("places", {
            "q": query,
            "loc": location,
            "r": radius,
            "rubric": rubric_id
        })
        
        cached = await self._get_cached(cache_key)
        if cached:
            return cached
        
        params = {
            "q": query,
            "region_id": self.NIZHNY_NOVGOROD_REGION_ID,
            "location": f"{location[1]},{location[0]}",
            "radius": radius,
            "page_size": limit,
            "fields": "items.point,items.address,items.schedule,items.contact_groups,items.rubrics"
        }
        
        if rubric_id:
            params["rubric_id"] = rubric_id
        
        data = await self._request(self.PLACES_URL, params)
        
        places = []
        if data and "result" in data and "items" in data["result"]:
            places = data["result"]["items"]
            await self._set_cache(cache_key, places, ttl=3600)
            logger.info(f"✓ Found {len(places)} places for '{query}'")
        
        return places
    
    async def search_cafes(
        self,
        location: Tuple[float, float],
        radius_km: float = 1.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for cafes using 2GIS Suggest API + catalog search"""
        
        cache_key = self._cache_key("cafes", {"loc": location, "r": radius_km})
        cached = await self._get_cached(cache_key)
        if cached:
            return cached
        
        # Use catalog search with type=branch and specific categories
        params = {
            "region_id": self.NIZHNY_NOVGOROD_REGION_ID,
            "type": "branch",
            "q": "кафе ресторан",
            "point": f"{location[1]},{location[0]}",
            "radius": int(radius_km * 1000),
            "page_size": limit,
            "fields": "items.point,items.address_name,items.schedule,items.contact_groups"
        }
        
        data = await self._request(self.PLACES_URL, params)
        
        cafes = []
        if data and "result" in data and "items" in data["result"]:
            items = data["result"]["items"]
            
            for item in items:
                point = item.get("point", {})
                if not point or "lat" not in point:
                    continue
                
                parsed = {
                    "id": item.get("id"),
                    "name": item.get("name", "Кафе"),
                    "lat": point.get("lat"),
                    "lon": point.get("lon"),
                    "address": item.get("address_name", ""),
                    "rubrics": [],
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
            else:
                logger.warning(f"No cafes in response for {location}")
        else:
            logger.warning(f"Empty response from Places API for {location}")
        
        return cafes
        
        parsed_cafes = []
        for cafe in cafes:
            point = cafe.get("point", {})
            
            parsed = {
                "id": cafe.get("id"),
                "name": cafe.get("name", "Unknown Cafe"),
                "lat": point.get("lat"),
                "lon": point.get("lon"),
                "address": cafe.get("address_name", ""),
                "rubrics": [r.get("name") for r in cafe.get("rubrics", [])],
                "schedule": cafe.get("schedule", {}),
            }
            
            contact_groups = cafe.get("contact_groups", [])
            if contact_groups:
                contacts = contact_groups[0].get("contacts", [])
                for contact in contacts:
                    if contact.get("type") == "phone":
                        parsed["phone"] = contact.get("text")
                    elif contact.get("type") == "website":
                        parsed["website"] = contact.get("url")
            
            parsed_cafes.append(parsed)
        
        return parsed_cafes
    
    def parse_geometry(self, route_data: Dict[str, Any]) -> List[Tuple[float, float]]:
        """Parse route geometry from 2GIS response"""
        
        if not route_data:
            return []
        
        # Try to get geometry from different possible locations
        geometry = route_data.get("geometry")
        
        if not geometry:
            # Sometimes it's in maneuvers
            maneuvers = route_data.get("maneuvers", [])
            if maneuvers:
                points = []
                for m in maneuvers:
                    point = m.get("point")
                    if point and "lat" in point and "lon" in point:
                        points.append((point["lat"], point["lon"]))
                return points
            return []
        
        # Geometry can be string or dict
        if isinstance(geometry, str):
            try:
                geometry = json.loads(geometry)
            except:
                return []
        
        # GeoJSON format: coordinates are [lon, lat]
        if isinstance(geometry, dict):
            coords = geometry.get("coordinates", [])
            if coords and isinstance(coords[0], list):
                # LineString: [[lon, lat], [lon, lat], ...]
                return [(lat, lon) for lon, lat in coords]
        
        return []
    
    def calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Haversine distance in kilometers"""
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