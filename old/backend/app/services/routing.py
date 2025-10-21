import logging
from typing import List, Tuple, Optional, Dict, Any

from app.core.config import settings
from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


class RoutingService:
    """Routing service using 2GIS Routing API v7"""
    
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
        
        # If too many waypoints, split into chunks and merge
        if len(all_points) > 10:
            logger.info(f"Splitting {len(all_points)} waypoints into multiple routing requests")
            
            all_geometry = []
            chunk_size = 9  # Leave room for overlap
            
            for i in range(0, len(all_points) - 1, chunk_size):
                chunk_end = min(i + chunk_size + 1, len(all_points))
                chunk = all_points[i:chunk_end]
                
                logger.info(f"Routing chunk {i//chunk_size + 1}: points {i} to {chunk_end-1}")
                
                route = await self.get_walking_route(chunk)
                
                if route and route["geometry"]:
                    chunk_geometry = [[lat, lon] for lat, lon in route["geometry"]]
                    
                    # Skip first point if not first chunk (avoid duplicates)
                    if all_geometry and chunk_geometry:
                        chunk_geometry = chunk_geometry[1:]
                    
                    all_geometry.extend(chunk_geometry)
                else:
                    # Fallback to straight lines for this chunk
                    logger.warning(f"Chunk {i//chunk_size + 1} failed, using straight lines")
                    for point in chunk[1:]:
                        all_geometry.append([point[0], point[1]])
            
            if all_geometry:
                logger.info(f"✓ Merged route geometry: {len(all_geometry)} points from {(len(all_points)-1)//chunk_size + 1} chunks")
                return all_geometry
        else:
            # Single request for small routes
            route = await self.get_walking_route(all_points)
            
            if route and route["geometry"]:
                geometry = [[lat, lon] for lat, lon in route["geometry"]]
                logger.info(f"✓ Route geometry: {len(geometry)} points")
                return geometry
        
        logger.warning("⚠ Fallback to straight lines")
        return [[lat, lon] for lat, lon in all_points]

    def distance_from_geometry(self, geometry: List[List[float]]) -> float:
        if not geometry or len(geometry) < 2:
            return 0.0

        total = 0.0
        prev_lat, prev_lon = geometry[0]

        for lat, lon in geometry[1:]:
            total += self.calculate_distance_km(prev_lat, prev_lon, lat, lon)
            prev_lat, prev_lon = lat, lon

        return total
    
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
        """Get public transit route suggestion (NOT available free tier)"""
        
        distance = self.calculate_distance_km(
            start[0], start[1], end[0], end[1]
        )
        
        if distance < self.transit_threshold_km:
            return None
        
        logger.info(f"Transit would be useful for {distance:.2f}km, but API not available")
        
        return None
    
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