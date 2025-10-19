import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
import redis.asyncio as redis
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class TransitService:
    BASE_URL = "https://api.navitia.io/v1"
    DISTANCE_THRESHOLD_KM = 2.0

    _BEARING_DIRECTIONS = {
        (337.5, 360): "северной",
        (0, 22.5): "северной",
        (22.5, 67.5): "северо-восточной",
        (67.5, 112.5): "восточной",
        (112.5, 157.5): "юго-восточной",
        (157.5, 202.5): "южной",
        (202.5, 247.5): "юго-западной",
        (247.5, 292.5): "западной",
        (292.5, 337.5): "северо-западной",
    }
    
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
    
    async def _cache_result(
        self,
        from_coords: Tuple[float, float],
        to_coords: Tuple[float, float],
        data: Dict[str, Any],
    ) -> None:
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
        to_lon: float,
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
            "min_nb_transfers": 0,
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
        instructions: List[str] = []
        total_walking_min = 0
        previous_walk_section: Optional[Dict[str, Any]] = None

        for section in best_journey.get("sections", []):
            section_type = section.get("type")

            if section_type == "public_transport":
                display_info = section.get("display_informations", {})
                line_name = display_info.get("code") or display_info.get("name", "Unknown")
                direction = display_info.get("direction", "")

                from_stop = section.get("from", {})
                to_stop = section.get("to", {})
                from_coord = from_stop.get("coord", {})
                to_coord = to_stop.get("coord", {})

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

                platform = (
                    from_stop.get("stop_point", {})
                    .get("platform", {})
                    .get("name")
                    or from_stop.get("stop_point", {}).get("platform_code")
                )
                boarding_side = self._infer_boarding_side(previous_walk_section, from_coord)
                departure_time = self._format_time(section.get("departure_date_time"))
                arrival_time = self._format_time(section.get("arrival_date_time"))

                transit_lines.append({
                    "line": line_name,
                    "direction": direction,
                    "from_stop": from_stop.get("name"),
                    "to_stop": to_stop.get("name"),
                    "duration_min": section.get("duration", 0) // 60,
                    "departure_time": departure_time,
                    "arrival_time": arrival_time,
                    "platform": platform,
                    "commercial_mode": display_info.get("commercial_mode"),
                    "physical_mode": display_info.get("physical_mode"),
                })

                sections.append({
                    "type": "transit",
                    "line": line_name,
                    "direction": direction,
                    "from": from_stop.get("name"),
                    "to": to_stop.get("name"),
                    "duration_min": section.get("duration", 0) // 60,
                    "departure_time": departure_time,
                    "arrival_time": arrival_time,
                    "platform": platform,
                    "boarding_side": boarding_side,
                })

                instructions.append(
                    self._build_boarding_instruction(
                        line_name=line_name,
                        direction=direction,
                        stop_name=from_stop.get("name"),
                        departure_time=departure_time,
                        platform=platform,
                        boarding_side=boarding_side,
                    )
                )

                instructions.append(
                    self._build_alighting_instruction(
                        stop_name=to_stop.get("name"),
                        arrival_time=arrival_time,
                        line_name=line_name,
                    )
                )

                previous_walk_section = None

            elif section_type == "street_network" and section.get("mode") == "walking":
                walk_minutes = section.get("duration", 0) // 60
                total_walking_min += walk_minutes
                sections.append({
                    "type": "walk",
                    "duration_min": walk_minutes,
                    "distance_m": section.get("length", 0),
                })
                previous_walk_section = section

        instructions = [inst for inst in instructions if inst]

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
            "instructions": instructions,
            "total_walking_min": total_walking_min,
        }

    def _build_transit_summary(self, lines: List[Dict[str, Any]]) -> str:
        if not lines:
            return ""

        if len(lines) == 1:
            line = lines[0]
            direction = f" до {line['to_stop']}" if line.get("to_stop") else ""
            mode = line.get("commercial_mode") or "маршрут"
            return f"{mode.capitalize()} {line['line']}{direction}"
        else:
            line_names = [l["line"] for l in lines]
            return f"Маршруты: {', '.join(line_names)}"

    def _infer_boarding_side(
        self,
        walk_section: Optional[Dict[str, Any]],
        stop_coord: Dict[str, Any],
    ) -> Optional[str]:
        if not walk_section:
            return None

        geojson = walk_section.get("geojson", {})
        coordinates = geojson.get("coordinates")
        if not coordinates:
            return None

        if len(coordinates) >= 2:
            p1 = coordinates[-2]
            p2 = coordinates[-1]
        else:
            p1 = coordinates[0]
            p2 = stop_coord and [stop_coord.get("lon"), stop_coord.get("lat")]

        if not p1 or not p2 or None in p1 or None in p2:
            return None

        lon1, lat1 = p1
        lon2, lat2 = p2
        bearing = self._calculate_bearing(lat1, lon1, lat2, lon2)

        for (start, end), direction in self._BEARING_DIRECTIONS.items():
            if start <= bearing < end or (start > end and (bearing >= start or bearing < end)):
                return direction
        return None

    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import atan2, cos, radians, sin

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        dlon = radians(lon2 - lon1)

        x = sin(dlon) * cos(lat2_rad)
        y = cos(lat1_rad) * sin(lat2_rad) - sin(lat1_rad) * cos(lat2_rad) * cos(dlon)
        bearing = (atan2(x, y) * 180 / 3.141592653589793 + 360) % 360
        return bearing

    def _build_boarding_instruction(
        self,
        line_name: Optional[str],
        direction: Optional[str],
        stop_name: Optional[str],
        departure_time: Optional[str],
        platform: Optional[str],
        boarding_side: Optional[str],
    ) -> str:
        parts = []
        if stop_name:
            parts.append(f"Сядьте на остановке «{stop_name}»")
        if platform:
            parts.append(f"платформа {platform}")
        if boarding_side:
            parts.append(f"(сторона: {boarding_side})")
        if line_name:
            parts.append(f"на маршрут {line_name}")
        if direction:
            parts.append(f"в сторону {direction}")
        if departure_time:
            parts.append(f"отправление в {departure_time}")
        return ", ".join(parts)

    def _build_alighting_instruction(
        self,
        stop_name: Optional[str],
        arrival_time: Optional[str],
        line_name: Optional[str],
    ) -> str:
        if not stop_name:
            return "Выйдите на нужной остановке"

        time_part = f" в {arrival_time}" if arrival_time else ""
        line_part = f" из {line_name}" if line_name else ""
        return f"Выйдите на остановке «{stop_name}»{time_part}{line_part}"

    def _format_time(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            parsed = datetime.strptime(value, "%Y%m%dT%H%M%S")
            return parsed.strftime("%H:%M")
        except Exception:
            return None

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

