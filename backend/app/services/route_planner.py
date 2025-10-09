from datetime import datetime, timedelta
from typing import List, Tuple
import numpy as np
from scipy.spatial.distance import cdist

from app.core.config import settings
from app.models.poi import POI


class RoutePlanner:
    def __init__(self):
        self.walk_speed_kmh = settings.DEFAULT_WALK_SPEED_KMH
    
    def calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        dlon = np.radians(lon2 - lon1)
        dlat = np.radians(lat2 - lat1)
        
        a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c
    
    def calculate_walk_time_minutes(self, distance_km: float) -> int:
        return int((distance_km / self.walk_speed_kmh) * 60) + 5
    
    def optimize_route(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[POI],
        available_hours: float,
    ) -> Tuple[List[POI], float]:
        if not pois:
            return [], 0.0
        
        available_minutes = available_hours * 60
        
        coords = np.array([[poi.lat, poi.lon] for poi in pois])
        start_coord = np.array([[start_lat, start_lon]])
        
        current_pos = start_coord[0]
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
    
    def insert_coffee_breaks(
        self,
        route: List[POI],
        coffee_interval_minutes: int,
        coffee_pois: List[POI],
    ) -> List[POI]:
        if not coffee_pois or not route:
            return route
        
        result = []
        elapsed_time = 0
        
        for poi in route:
            result.append(poi)
            elapsed_time += poi.avg_visit_minutes
            
            if elapsed_time >= coffee_interval_minutes and len(result) < len(route):
                nearest_coffee = self._find_nearest_coffee(poi, coffee_pois)
                if nearest_coffee and nearest_coffee not in result:
                    result.append(nearest_coffee)
                    elapsed_time = 0
        
        return result
    
    def _find_nearest_coffee(self, from_poi: POI, coffee_pois: List[POI]) -> POI | None:
        min_dist = float('inf')
        nearest = None
        
        for coffee_poi in coffee_pois:
            dist = self.calculate_distance_km(
                from_poi.lat, from_poi.lon,
                coffee_poi.lat, coffee_poi.lon
            )
            if dist < min_dist:
                min_dist = dist
                nearest = coffee_poi
        
        return nearest


route_planner = RoutePlanner()