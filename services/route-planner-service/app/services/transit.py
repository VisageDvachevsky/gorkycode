"""Transit assistance for the route planner service."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


class TransitAdvisor:
    """Suggests public transport legs using 2GIS (with Navitia fallback)."""

    NAVITIA_BASE_URL = "https://api.navitia.io/v1"

    def __init__(self) -> None:
        self.distance_threshold_km = settings.TRANSIT_DISTANCE_THRESHOLD_KM
        self.redis_client: Optional[redis.Redis] = None
        self.navitia_api_key = settings.NAVITIA_API_KEY

        if not self.navitia_api_key:
            logger.info("Navitia API key not configured – relying solely on 2GIS transit")

    async def connect_redis(self) -> None:
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
            logger.info("Transit advisor: connected to Redis cache")

    def _cache_key(self, start: Tuple[float, float], end: Tuple[float, float]) -> str:
        payload = json.dumps({"s": start, "e": end}, sort_keys=True)
        return f"transit:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"

    async def _get_cached(
        self, start: Tuple[float, float], end: Tuple[float, float]
    ) -> Optional[Dict[str, Any]]:
        if not self.redis_client:
            await self.connect_redis()

        cached = await self.redis_client.get(self._cache_key(start, end))  # type: ignore[arg-type]
        if cached:
            return json.loads(cached)
        return None

    async def _set_cache(
        self, start: Tuple[float, float], end: Tuple[float, float], value: Dict[str, Any]
    ) -> None:
        if not self.redis_client:
            await self.connect_redis()

        await self.redis_client.set(  # type: ignore[arg-type]
            self._cache_key(start, end), json.dumps(value), ex=1800
        )

    async def suggest_transit(
        self, start: Tuple[float, float], end: Tuple[float, float]
    ) -> Optional[Dict[str, Any]]:
        """Return rich information about the best public transport option."""

        crow_distance = twogis_client.calculate_distance(*start, *end)
        if crow_distance < self.distance_threshold_km:
            return None

        cached = await self._get_cached(start, end)
        if cached:
            return cached

        # 1) Try 2GIS public transport API first.
        try:
            raw_transit = await twogis_client.get_public_transport_route(start, end)
            parsed = twogis_client.parse_transit_route(raw_transit)
            if parsed:
                parsed.update(
                    {
                        "provider": "2gis",
                        "summary": parsed.get("summary")
                        or f"Маршрут {parsed.get('line_name', '')}".strip(),
                        "instructions": self._build_transit_instructions(parsed),
                        "walk_to_board_m": None,
                        "walk_from_alight_m": None,
                        "departure_time": parsed.get("departure_time"),
                        "arrival_time": parsed.get("arrival_time"),
                    }
                )
                await self._set_cache(start, end, parsed)
                return parsed
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("2GIS public transport lookup failed: %s", exc)

        # 2) Fallback to Navitia if available.
        if not self.navitia_api_key:
            return None

        navitia = await self._navitia_route(start, end)
        if navitia:
            await self._set_cache(start, end, navitia)
        return navitia

    def _build_transit_instructions(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        instructions: List[Dict[str, Any]] = []

        boarding = data.get("boarding_stop") or {}
        alighting = data.get("alighting_stop") or {}

        if boarding.get("name"):
            instructions.append(
                {
                    "instruction": f"Двигайтесь к остановке {boarding['name']}",
                    "distance_m": None,
                    "duration_s": None,
                }
            )

        if data.get("line_name"):
            vehicle = data.get("vehicle_type") or "транспорт"
            instructions.append(
                {
                    "instruction": (
                        f"Сядьте на {vehicle} {data['line_name']}"
                        + (
                            f" до {alighting.get('name')}"
                            if alighting.get("name")
                            else ""
                        )
                    ),
                    "distance_m": None,
                    "duration_s": None,
                }
            )

        if alighting.get("name"):
            instructions.append(
                {
                    "instruction": f"Выйдите на остановке {alighting['name']}",
                    "distance_m": None,
                    "duration_s": None,
                }
            )

        return instructions

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _navitia_route(
        self, start: Tuple[float, float], end: Tuple[float, float]
    ) -> Optional[Dict[str, Any]]:
        if not self.navitia_api_key:
            return None

        params = {
            "from": f"{start[1]};{start[0]}",
            "to": f"{end[1]};{end[0]}",
            "count": 3,
            "datetime_represents": "departure",
        }

        headers = {"Authorization": self.navitia_api_key}

        async with httpx.AsyncClient(timeout=40) as client:
            response = await client.get(
                f"{self.NAVITIA_BASE_URL}/coverage/ru/journeys",
                params=params,
                headers=headers,
            )

        if response.status_code != 200:
            if response.status_code not in (400, 404):
                logger.warning(
                    "Navitia returned %s: %s", response.status_code, response.text[:200]
                )
            return None

        data = response.json()
        parsed = self._parse_navitia_response(data)
        if parsed:
            parsed["provider"] = "navitia"
        return parsed

    def _parse_navitia_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        journeys = data.get("journeys", [])
        if not journeys:
            return None

        journey = journeys[0]
        total_duration_min = journey.get("duration", 0) / 60.0
        departure_time = journey.get("departure_date_time")
        arrival_time = journey.get("arrival_date_time")

        transit_sections = [
            section
            for section in journey.get("sections", [])
            if section.get("type") == "public_transport"
        ]

        if not transit_sections:
            return None

        main_section = transit_sections[0]
        display = main_section.get("display_informations", {})

        boarding_from = main_section.get("from", {})
        alighting_to = main_section.get("to", {})

        sections = journey.get("sections", [])
        instructions: List[Dict[str, Any]] = []
        walk_to_board = 0.0
        walk_from_alight = 0.0
        total_distance = 0.0

        for section in sections:
            section_type = section.get("type")
            if section_type == "street_network" and section.get("mode") == "walking":
                distance = float(section.get("length", 0) or 0.0)
                duration_sec = float(section.get("duration", 0) or 0.0)
                total_distance += distance / 1000.0
                instruction = "Прогулка пешком"
                if section.get("from", {}).get("name") and section.get("to", {}).get("name"):
                    instruction = (
                        f"Идите от {section['from']['name']} до {section['to']['name']}"
                    )
                if not instructions:
                    walk_to_board += distance
                else:
                    walk_from_alight += distance
                instructions.append(
                    {
                        "instruction": instruction,
                        "distance_m": distance,
                        "duration_s": duration_sec,
                    }
                )
            elif section_type == "public_transport":
                distance = float(section.get("length", 0) or 0.0)
                total_distance += distance / 1000.0
                line = display.get("commercial_mode", "транспорт")
                line_code = display.get("code") or display.get("name")
                instruction = f"Поездка на {line} {line_code}"
                if section.get("to", {}).get("name"):
                    instruction += f" до {section['to']['name']}"
                instructions.append(
                    {
                        "instruction": instruction,
                        "distance_m": distance,
                        "duration_s": float(section.get("duration", 0) or 0.0),
                    }
                )

        summary = (
            f"{display.get('commercial_mode', 'Маршрут')} {display.get('code', '')}"
        ).strip()

        return {
            "summary": summary,
            "line_name": display.get("code") or display.get("name", ""),
            "vehicle_type": display.get("commercial_mode", ""),
            "direction": display.get("direction", ""),
            "vehicle_number": display.get("headsign", ""),
            "duration_min": total_duration_min,
            "distance_km": total_distance,
            "boarding_stop": {
                "name": boarding_from.get("name", ""),
                "lat": boarding_from.get("coord", {}).get("lat"),
                "lon": boarding_from.get("coord", {}).get("lon"),
                "side": None,
            },
            "alighting_stop": {
                "name": alighting_to.get("name", ""),
                "lat": alighting_to.get("coord", {}).get("lat"),
                "lon": alighting_to.get("coord", {}).get("lon"),
                "side": None,
            },
            "notes": [display.get("headsign", "")],
            "instructions": instructions,
            "walk_to_board_m": walk_to_board,
            "walk_from_alight_m": walk_from_alight,
            "departure_time": departure_time,
            "arrival_time": arrival_time,
        }


transit_advisor = TransitAdvisor()
