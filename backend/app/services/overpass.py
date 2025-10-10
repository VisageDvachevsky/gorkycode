import hashlib
import json
import logging
from typing import List, Optional, Dict, Any
import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)


class OverpassService:
    BASE_URL = "https://overpass-api.de/api/interpreter"
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
            logger.info("Overpass service: Redis connected")
    
    def _get_cache_key(self, query: str) -> str:
        return f"overpass:{hashlib.sha256(query.encode()).hexdigest()}"
    
    async def _get_cached(self, query: str) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(query)
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            logger.info("✓ Overpass cache hit")
            return json.loads(cached)
        return None
    
    async def _cache_result(self, query: str, data: Dict[str, Any]) -> None:
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(query)
        await self.redis_client.set(
            cache_key,
            json.dumps(data),
            ex=86400
        )
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True
    )
    async def _fetch_overpass(self, query: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(
                    self.BASE_URL,
                    data={"data": query},
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Overpass error: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Overpass request failed: {str(e)}")
                raise
    
    async def search_cafes(
        self,
        lat: float,
        lon: float,
        radius_km: float = 1.0,
        cuisine: Optional[str] = None,
        dietary: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        radius_m = int(radius_km * 1000)
        
        filters = []
        if cuisine:
            filters.append(f'["cuisine"~"{cuisine}",i]')
        if dietary:
            filters.append(f'["{dietary}"="yes"]')
        
        filter_str = "".join(filters) if filters else ""
        
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="cafe"]{filter_str}(around:{radius_m},{lat},{lon});
          node["amenity"="restaurant"]{filter_str}(around:{radius_m},{lat},{lon});
          node["amenity"="bar"]["food"="yes"]{filter_str}(around:{radius_m},{lat},{lon});
        );
        out body;
        """
        
        cached = await self._get_cached(query)
        if cached:
            return self._parse_overpass_response(cached, tags)
        
        logger.info(f"Searching cafes: radius={radius_km}km, cuisine={cuisine}, dietary={dietary}")
        
        try:
            data = await self._fetch_overpass(query)
            if data:
                await self._cache_result(query, data)
                return self._parse_overpass_response(data, tags)
        except Exception as e:
            logger.error(f"Overpass search failed: {str(e)}")
        
        return []
    
    def _parse_overpass_response(
        self,
        data: Dict[str, Any],
        required_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        cafes = []
        
        for element in data.get("elements", []):
            if element.get("type") != "node":
                continue
            
            tags = element.get("tags", {})
            name = tags.get("name", "Unknown Cafe")
            
            if required_tags:
                tag_match = any(
                    tag.lower() in str(tags).lower() 
                    for tag in required_tags
                )
                if not tag_match:
                    continue
            
            cafe = {
                "osm_id": element.get("id"),
                "name": name,
                "lat": element.get("lat"),
                "lon": element.get("lon"),
                "amenity": tags.get("amenity", "cafe"),
                "cuisine": tags.get("cuisine", ""),
                "diet": {
                    "vegetarian": tags.get("diet:vegetarian") == "yes",
                    "vegan": tags.get("diet:vegan") == "yes",
                    "halal": tags.get("diet:halal") == "yes",
                    "kosher": tags.get("diet:kosher") == "yes",
                },
                "opening_hours": tags.get("opening_hours", ""),
                "phone": tags.get("phone", ""),
                "website": tags.get("website", ""),
                "outdoor_seating": tags.get("outdoor_seating") == "yes",
                "wifi": tags.get("internet_access") in ["yes", "wlan", "wifi"],
            }
            
            cafes.append(cafe)
        
        logger.info(f"✓ Found {len(cafes)} cafes from OSM")
        return cafes
    
    async def find_best_cafe(
        self,
        from_lat: float,
        from_lon: float,
        preferences: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        cafes = await self.search_cafes(
            lat=from_lat,
            lon=from_lon,
            radius_km=preferences.get("search_radius", 0.5),
            cuisine=preferences.get("cuisine"),
            dietary=preferences.get("dietary"),
            tags=preferences.get("tags")
        )
        
        if not cafes:
            return None
        
        scored_cafes = []
        for cafe in cafes:
            score = 0.0
            
            dist = self._haversine_distance(
                from_lat, from_lon,
                cafe["lat"], cafe["lon"]
            )
            score += max(0, 1.0 - dist)
            
            if preferences.get("dietary"):
                diet_key = preferences["dietary"]
                if cafe["diet"].get(diet_key):
                    score += 0.5
            
            if preferences.get("outdoor_seating") and cafe["outdoor_seating"]:
                score += 0.2
            
            if preferences.get("wifi") and cafe["wifi"]:
                score += 0.2
            
            if cafe["cuisine"]:
                score += 0.1
            
            scored_cafes.append((cafe, score))
        
        scored_cafes.sort(key=lambda x: x[1], reverse=True)
        return scored_cafes[0][0] if scored_cafes else None
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371
        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        dlon = radians(lon2 - lon1)
        dlat = radians(lat2 - lat1)
        
        a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        return R * c


overpass_service = OverpassService()