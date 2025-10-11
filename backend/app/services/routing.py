import logging
from typing import List, Tuple, Optional, Dict, Any

from app.core.config import settings
from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


class RoutingService:
    """Routing service using 2GIS Directions and Public Transport APIs"""
    
    def __init__(self):
        self.transit_threshold_km = settings.TRANSIT_DISTANCE_THRESHOLD_KM
    
    async def get_walking_route(
        self,
        points: List[Tuple[float, float]]
    ) -> Optional[Dict[str, Any]]:
        """Get detailed walking route with real road geometry"""
        
        if len(points) < 2:
            return None
        
        route_data = await twogis_client.get_walking_route(points)
        
        if not route_data:
            logger.warning(f"Failed to get walking route for {len(points)} points")
            return None
        
        return {
            "distance_km": route_data.get("distance", 0) / 1000,
            "duration_min": route_data.get("duration", 0) / 60,
            "geometry": twogis_client.parse_geometry(route_data),
            "raw": route_data
        }
    
    async def calculate_route_geometry(
        self,
        start: Tuple[float, float],
        waypoints: List[Tuple[float, float]]
    ) -> List[List[float]]:
        """Calculate complete route geometry with all waypoints"""
        
        all_points = [start] + waypoints
        route = await self.get_walking_route(all_points)
        
        if route and route["geometry"]:
            geometry = [[lat, lon] for lat, lon in route["geometry"]]
            logger.info(f"✓ Route geometry: {len(geometry)} points")
            return geometry
        
        logger.warning("⚠ Fallback to straight lines")
        return [[lat, lon] for lat, lon in all_points]
    
    async def get_route_distance(
        self,
        start: Tuple[float, float],
        waypoints: List[Tuple[float, float]]
    ) -> float:
        """Get total route distance in kilometers"""
        
        route = await self.get_walking_route([start] + waypoints)
        
        if route:
            return route["distance_km"]
        
        total = 0.0
        all_points = [start] + waypoints
        for i in range(len(all_points) - 1):
            total += self.calculate_distance_km(
                all_points[i][0], all_points[i][1],
                all_points[i+1][0], all_points[i+1][1]
            )
        return total
    
    async def get_transit_suggestion(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float]
    ) -> Optional[Dict[str, Any]]:
        """Get public transit route if distance exceeds threshold"""
        
        distance = self.calculate_distance_km(
            start[0], start[1], end[0], end[1]
        )
        
        if distance < self.transit_threshold_km:
            return None
        
        logger.info(f"Distance {distance:.2f}km exceeds threshold, checking transit...")
        
        transit_data = await twogis_client.get_transit_route(start, end)
        
        if not transit_data:
            return None
        
        return self._parse_transit_response(transit_data, distance)
    
    def _parse_transit_response(
        self,
        data: Dict[str, Any],
        walking_distance: float
    ) -> Optional[Dict[str, Any]]:
        """Parse 2GIS Public Transport API response"""
        
        if not data or "routes" not in data:
            return None
        
        routes = data.get("routes", [])
        if not routes:
            return None
        
        best_route = routes[0]
        
        total_duration = best_route.get("total_duration", 0) / 60
        walking_duration = walking_distance / settings.DEFAULT_WALK_SPEED_KMH * 60
        
        if total_duration >= walking_duration * 0.7:
            logger.info("Transit not faster than walking, skipping")
            return None
        
        legs = best_route.get("legs", [])
        transit_legs = [leg for leg in legs if leg.get("type") == "pt"]
        
        if not transit_legs:
            return None
        
        transport_lines = []
        for leg in transit_legs:
            transport = leg.get("transport", {})
            transport_lines.append({
                "type": transport.get("type", "bus"),
                "name": transport.get("name", ""),
                "color": transport.get("color", ""),
            })
        
        return {
            "total_duration_min": total_duration,
            "walking_duration_min": walking_duration,
            "time_saved_min": walking_duration - total_duration,
            "transport_lines": transport_lines,
            "suggestion": self._build_transit_suggestion(transport_lines),
            "raw": best_route
        }
    
    def _build_transit_suggestion(self, lines: List[Dict[str, Any]]) -> str:
        """Build human-readable transit suggestion"""
        
        if not lines:
            return ""
        
        if len(lines) == 1:
            line = lines[0]
            return f"Можно доехать на {line['type']} {line['name']}"
        else:
            line_names = [f"{l['type']} {l['name']}" for l in lines]
            return f"Можно доехать с пересадкой: {' → '.join(line_names)}"
    
    def calculate_distance_km(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Haversine distance calculation"""
        
        return twogis_client.calculate_distance(lat1, lon1, lat2, lon2)
    
    def should_suggest_transit(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> bool:
        """Check if transit should be suggested based on distance"""
        
        distance = self.calculate_distance_km(lat1, lon1, lat2, lon2)
        return distance >= self.transit_threshold_km


routing_service = RoutingService()