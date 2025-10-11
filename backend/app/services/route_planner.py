from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, TYPE_CHECKING
import numpy as np

from app.core.config import settings
from app.models.poi import POI

if TYPE_CHECKING:
    from app.services.coffee import CoffeeService

import logging
logger = logging.getLogger(__name__)


class RoutePlanner:
    def __init__(self):
        self.walk_speed_kmh = settings.DEFAULT_WALK_SPEED_KMH
    
    def calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance"""
        R = 6371.0
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlon = np.radians(lon2 - lon1)
        dlat = np.radians(lat2 - lat1)
        
        a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c
    
    def calculate_walk_time_minutes(self, distance_km: float) -> int:
        """Calculate walking time with buffer"""
        return int((distance_km / self.walk_speed_kmh) * 60) + 5
    
    def optimize_route(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[POI],
        available_hours: float,
    ) -> Tuple[List[POI], float]:
        """Optimize route using greedy nearest neighbor"""
        
        if not pois:
            return [], 0.0
        
        available_minutes = available_hours * 60
        
        current_pos = np.array([start_lat, start_lon])
        remaining_pois = list(pois)
        ordered_route = []
        total_time = 0
        total_distance = 0.0
        
        while remaining_pois and total_time < available_minutes:
            distances = []
            for poi in remaining_pois:
                dist = self.calculate_distance_km(
                    current_pos[0], current_pos[1],
                    poi.lat, poi.lon
                )
                distances.append(dist)
            
            nearest_idx = np.argmin(distances)
            nearest_poi = remaining_pois[nearest_idx]
            nearest_dist = distances[nearest_idx]
            
            walk_time = self.calculate_walk_time_minutes(nearest_dist)
            poi_time = nearest_poi.avg_visit_minutes
            
            if total_time + walk_time + poi_time > available_minutes:
                break
            
            ordered_route.append(nearest_poi)
            total_time += walk_time + poi_time
            total_distance += nearest_dist
            current_pos = np.array([nearest_poi.lat, nearest_poi.lon])
            remaining_pois.pop(nearest_idx)
        
        return ordered_route, total_distance
    
    async def insert_smart_coffee_breaks(
        self,
        route: List[POI],
        interval_minutes: int,
        preferences: Dict[str, Any],
        coffee_service: "CoffeeService",
        session: Any = None
    ) -> List[POI]:
        """Insert coffee breaks using 2GIS Places API with DB fallback"""
        
        if not route or len(route) < 2:
            return route
        
        result = []
        time_since_last_break = 0
        
        for i, poi in enumerate(route):
            result.append(poi)
            time_since_last_break += poi.avg_visit_minutes
            
            if time_since_last_break >= interval_minutes and i < len(route) - 1:
                next_poi = route[i + 1]
                
                cafe_data = await coffee_service.find_best_cafe_for_route(
                    from_poi=poi,
                    to_poi=next_poi,
                    preferences=preferences,
                    session=session
                )
                
                if cafe_data:
                    cafe_poi = coffee_service.convert_to_poi(cafe_data)
                    
                    if cafe_poi.id not in [p.id for p in result]:
                        result.append(cafe_poi)
                        time_since_last_break = 0
                        logger.info(f"✓ Added coffee break: {cafe_poi.name}")
        
        return result
        
        return result


route_planner = RoutePlanner()