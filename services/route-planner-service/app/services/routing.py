import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.transit import transit_service
from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


class RoutingService:
    """Routing utilities backed by 2GIS."""

    def __init__(self) -> None:
        self.transit_threshold_km = settings.TRANSIT_DISTANCE_THRESHOLD_KM
        self.walk_speed_kmh = settings.DEFAULT_WALK_SPEED_KMH

    async def get_walking_route(
        self,
        points: List[Tuple[float, float]],
    ) -> Optional[Dict[str, Any]]:
        if len(points) < 2:
            return None

        route_data = await twogis_client.get_walking_route(points)
        if not route_data:
            logger.warning("Failed to get walking route for %s points", len(points))
            return None

        return {
            "distance_km": route_data.get("distance", 0) / 1000,
            "duration_min": route_data.get("duration", 0) / 60,
            "geometry": twogis_client.parse_geometry(route_data),
            "raw": route_data,
        }

    async def calculate_route_geometry(
        self,
        start: Tuple[float, float],
        waypoints: List[Tuple[float, float]],
    ) -> List[List[float]]:
        all_points = [start] + waypoints

        if len(all_points) > 10:
            logger.info("Splitting %s waypoints into multiple routing requests", len(all_points))
            all_geometry: List[List[float]] = []
            chunk_size = 9

            for i in range(0, len(all_points) - 1, chunk_size):
                chunk_end = min(i + chunk_size + 1, len(all_points))
                chunk = all_points[i:chunk_end]

                logger.info("Routing chunk %s: points %s-%s", i // chunk_size + 1, i, chunk_end - 1)

                route = await self.get_walking_route(chunk)
                if route and route["geometry"]:
                    chunk_geometry = [[lat, lon] for lat, lon in route["geometry"]]
                    if all_geometry and chunk_geometry:
                        chunk_geometry = chunk_geometry[1:]
                    all_geometry.extend(chunk_geometry)
                else:
                    logger.warning("Chunk %s failed, using straight lines", i // chunk_size + 1)
                    for point in chunk[1:]:
                        all_geometry.append([point[0], point[1]])

            if all_geometry:
                logger.info("✓ Merged route geometry: %s points", len(all_geometry))
                return all_geometry
        else:
            route = await self.get_walking_route(all_points)
            if route and route["geometry"]:
                geometry = [[lat, lon] for lat, lon in route["geometry"]]
                logger.info("✓ Route geometry: %s points", len(geometry))
                return geometry

        logger.warning("⚠ Fallback to straight lines")
        return [[lat, lon] for lat, lon in all_points]

    async def get_route_distance(
        self,
        start: Tuple[float, float],
        waypoints: List[Tuple[float, float]],
    ) -> float:
        route = await self.get_walking_route([start] + waypoints)
        if route:
            return route["distance_km"]

        total = 0.0
        all_points = [start] + waypoints
        for i in range(len(all_points) - 1):
            total += self.calculate_distance_km(
                all_points[i][0],
                all_points[i][1],
                all_points[i + 1][0],
                all_points[i + 1][1],
            )
        return total

    async def get_transit_suggestion(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
    ) -> Optional[Dict[str, Any]]:
        distance = self.calculate_distance_km(start[0], start[1], end[0], end[1])

        if not transit_service.should_suggest_transit(distance):
            return None

        walking_minutes = self._estimate_walking_time(distance)

        try:
            transit_plan = await transit_service.get_transit_route(
                start[0],
                start[1],
                end[0],
                end[1],
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Transit lookup failed: %s", exc)
            return None

        if not transit_plan:
            return None

        transit_minutes = transit_plan.get("total_duration_min") or walking_minutes
        time_saved = max(0, walking_minutes - transit_minutes)

        summary = transit_plan.get("summary") or "Общественный транспорт доступен"

        return {
            "suggestion": summary,
            "time_saved_min": time_saved,
            "instructions": transit_plan.get("instructions", []),
            "boarding_stop": transit_plan.get("boarding_stop"),
            "alighting_stop": transit_plan.get("alighting_stop"),
            "transit_lines": transit_plan.get("transit_lines", []),
            "total_duration_min": transit_minutes,
            "total_walking_min": transit_plan.get("total_walking_min"),
        }

    def calculate_distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        return twogis_client.calculate_distance(lat1, lon1, lat2, lon2)

    def should_suggest_transit(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> bool:
        distance = self.calculate_distance_km(lat1, lon1, lat2, lon2)
        return distance >= self.transit_threshold_km

    def _estimate_walking_time(self, distance_km: float) -> float:
        return (distance_km / self.walk_speed_kmh) * 60


routing_service = RoutingService()
