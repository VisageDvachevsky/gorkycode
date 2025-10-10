import hashlib
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)


class TransitService:
    BASE_URL = "https://api.navitia.io/v1"
    DISTANCE_THRESHOLD_KM = 2.0
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.api_key = settings.NAVITIA_API_KEY
        
        if not self.api_key:
            logger.warning("Navitia API key not configured, transit suggestions disabled")
    
    async def connect_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
            logger.info("Transit service: Redis connected")
    
    def _get_cache_key(self, from_coords: Tuple[float, float], to_coords: Tuple[float, float]) -> str:
        key_str = f"{from_coords[0]:.4f},{from_coords[1]:.4f}-{to_coords[0]:.4f},{to_coords[1]:.4f}"
        return f"transit:{hashlib.sha256(key_str.encode()).hexdigest()}"
    
    async def _get_cached(self, from_coords: Tuple[float, float], to_coords: Tuple[float, float]) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(from_coords, to_coords)
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            logger.info("✓ Transit cache hit")
            return json.loads(cached)
        return None
    
    async def _cache_result(self, from_coords: Tuple[float, float], to_coords: Tuple[float, float], data: Dict[str, Any]) -> None:
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(from_coords, to_coords)
        await self.redis_client.set(
            cache_key,
            json.dumps(data),
            ex=3600
        )
    
    def should_suggest_transit(self, distance_km: float) -> bool:
        return distance_km >= self.DISTANCE_THRESHOLD_KM
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True
    )
    async def get_transit_route(
        self,
        from_lat: float,
        from_lon: float,
        to_lat: float,
        to_lon: float
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        
        from_coords = (from_lat, from_lon)
        to_coords = (to_lat, to_lon)
        
        cached = await self._get_cached(from_coords, to_coords)
        if cached:
            return cached
        
        url = f"{self.BASE_URL}/coverage/ru/journeys"
        
        params = {
            "from": f"{from_lon};{from_lat}",
            "to": f"{to_lon};{to_lat}",
            "datetime_represents": "departure",
            "count": 3,
        }
        
        headers = {
            "Authorization": self.api_key
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                logger.info(f"Requesting transit: ({from_lat:.4f},{from_lon:.4f}) -> ({to_lat:.4f},{to_lon:.4f})")
                
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    parsed = self._parse_navitia_response(data)
                    
                    if parsed:
                        await self._cache_result(from_coords, to_coords, parsed)
                        logger.info(f"✓ Transit route found: {parsed.get('summary', 'N/A')}")
                        return parsed
                    
                elif response.status_code == 404:
                    logger.info("No transit coverage for this area")
                    return None
                else:
                    logger.error(f"Navitia error: {response.status_code}")
                    return None
                    
            except Exception as e:
                logger.error(f"Transit request failed: {str(e)}")
                raise
        
        return None
    
    def _parse_navitia_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        journeys = data.get("journeys", [])
        
        if not journeys:
            return None
        
        best_journey = journeys[0]
        
        sections = []
        boarding_stop = None
        alighting_stop = None
        transit_lines = []
        
        for section in best_journey.get("sections", []):
            section_type = section.get("type")
            
            if section_type == "public_transport":
                display_info = section.get("display_informations", {})
                line_name = display_info.get("code") or display_info.get("name", "Unknown")
                direction = display_info.get("direction", "")
                
                from_stop = section.get("from", {})
                to_stop = section.get("to", {})
                
                if not boarding_stop:
                    boarding_stop = {
                        "name": from_stop.get("name", "Unknown"),
                        "lat": from_stop.get("coord", {}).get("lat"),
                        "lon": from_stop.get("coord", {}).get("lon"),
                    }
                
                alighting_stop = {
                    "name": to_stop.get("name", "Unknown"),
                    "lat": to_stop.get("coord", {}).get("lat"),
                    "lon": to_stop.get("coord", {}).get("lon"),
                }
                
                transit_lines.append({
                    "line": line_name,
                    "direction": direction,
                    "from_stop": from_stop.get("name"),
                    "to_stop": to_stop.get("name"),
                    "duration_min": section.get("duration", 0) // 60,
                })
                
                sections.append({
                    "type": "transit",
                    "line": line_name,
                    "direction": direction,
                    "from": from_stop.get("name"),
                    "to": to_stop.get("name"),
                    "duration_min": section.get("duration", 0) // 60,
                })
                
            elif section_type == "street_network" and section.get("mode") == "walking":
                sections.append({
                    "type": "walk",
                    "duration_min": section.get("duration", 0) // 60,
                    "distance_m": section.get("length", 0),
                })
        
        if not transit_lines:
            return None
        
        total_duration = best_journey.get("duration", 0) // 60
        
        summary = self._build_transit_summary(transit_lines)
        
        return {
            "summary": summary,
            "total_duration_min": total_duration,
            "boarding_stop": boarding_stop,
            "alighting_stop": alighting_stop,
            "sections": sections,
            "transit_lines": transit_lines,
        }
    
    def _build_transit_summary(self, lines: List[Dict[str, Any]]) -> str:
        if not lines:
            return ""
        
        if len(lines) == 1:
            line = lines[0]
            return f"Автобус/трамвай {line['line']} до {line['to_stop']}"
        else:
            line_names = [l["line"] for l in lines]
            return f"Маршруты: {', '.join(line_names)}"
    
    async def find_nearest_stop(
        self,
        lat: float,
        lon: float,
        radius_m: int = 500
    ) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        
        url = f"{self.BASE_URL}/coverage/ru/coords/{lon};{lat}/stop_points"
        
        params = {
            "distance": radius_m,
            "count": 5,
        }
        
        headers = {
            "Authorization": self.api_key
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    stops = data.get("stop_points", [])
                    
                    if stops:
                        stop = stops[0]
                        return {
                            "name": stop.get("name"),
                            "lat": stop.get("coord", {}).get("lat"),
                            "lon": stop.get("coord", {}).get("lon"),
                        }
                        
            except Exception as e:
                logger.error(f"Stop search failed: {str(e)}")
        
        return None


transit_service = TransitService()