from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, TYPE_CHECKING, Optional
import numpy as np

from app.core.config import settings
from app.models.poi import POI
from app.services.twogis_client import twogis_client

if TYPE_CHECKING:
    from app.services.coffee import CoffeeService

import logging
logger = logging.getLogger(__name__)


class RoutePlanner:
    def __init__(self):
        self.walk_speed_kmh = settings.DEFAULT_WALK_SPEED_KMH
    
    def calculate_walk_time_minutes(self, distance_km: float) -> int:
        return int((distance_km / self.walk_speed_kmh) * 60) + 5
    
    async def optimize_route(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[POI],
        available_hours: float,
    ) -> Tuple[List[POI], float]:
        if not pois:
            return [], 0.0
        
        available_minutes = available_hours * 60
        
        distance_matrix = await self._get_real_distance_matrix(
            start_lat, start_lon, pois
        )
        
        if distance_matrix is None:
            logger.warning("Distance Matrix API failed, using haversine fallback")
            return await self._optimize_route_haversine(
                start_lat, start_lon, pois, available_hours
            )
        
        route_indices, total_time, total_distance = self._greedy_nearest_neighbor(
            distance_matrix, pois, available_minutes
        )
        
        if not route_indices:
            return [], 0.0
        
        route_indices = self._two_opt_improve(
            route_indices, distance_matrix, pois, available_minutes
        )
        
        ordered_route = [pois[i] for i in route_indices]
        
        final_distance = 0.0
        prev_idx = -1
        for idx in route_indices:
            final_distance += distance_matrix[prev_idx + 1][idx + 1]
            prev_idx = idx
        
        logger.info(f"✓ Optimized route: {len(ordered_route)} POIs, {final_distance:.2f}km (real roads)")
        
        return ordered_route, final_distance
    
    async def _get_real_distance_matrix(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[POI]
    ) -> Optional[np.ndarray]:
        all_points = [(start_lat, start_lon)] + [(poi.lat, poi.lon) for poi in pois]
        
        # 2GIS free tier limit: 10x10 matrix maximum
        if len(all_points) > 10:
            logger.warning(f"Too many POIs ({len(pois)}) for Distance Matrix API (max 10 with free tier), using haversine fallback")
            return None
        
        try:
            matrix_data = await twogis_client.get_distance_matrix(
                sources=all_points,
                targets=all_points,
                transport="pedestrian"
            )
            
            if not matrix_data:
                return None
            
            matrix = twogis_client.parse_distance_matrix(
                matrix_data,
                num_sources=len(all_points),
                num_targets=len(all_points)
            )
            
            return np.array(matrix)
            
        except Exception as e:
            logger.error(f"Distance Matrix API error: {e}")
            return None
    
    def _greedy_nearest_neighbor(
        self,
        distance_matrix: np.ndarray,
        pois: List[POI],
        available_minutes: int
    ) -> Tuple[List[int], int, float]:
        n = len(pois)
        remaining = set(range(n))
        route = []
        total_time = 0
        total_distance = 0.0
        
        current_idx = -1
        
        while remaining and total_time < available_minutes:
            nearest_idx = None
            nearest_dist = float('inf')
            
            for poi_idx in remaining:
                dist = distance_matrix[current_idx + 1][poi_idx + 1]
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_idx = poi_idx
            
            if nearest_idx is None:
                break
            
            walk_time = self.calculate_walk_time_minutes(nearest_dist)
            poi_time = pois[nearest_idx].avg_visit_minutes
            
            if total_time + walk_time + poi_time > available_minutes:
                break
            
            route.append(nearest_idx)
            total_time += walk_time + poi_time
            total_distance += nearest_dist
            current_idx = nearest_idx
            remaining.remove(nearest_idx)
        
        return route, total_time, total_distance
    
    def _two_opt_improve(
        self,
        route: List[int],
        distance_matrix: np.ndarray,
        pois: List[POI],
        available_minutes: int,
        max_iterations: int = 10
    ) -> List[int]:
        if len(route) < 4:
            return route
        
        improved = True
        iteration = 0
        
        while improved and iteration < max_iterations:
            improved = False
            iteration += 1
            
            for i in range(len(route) - 2):
                for j in range(i + 2, len(route)):
                    current_dist = self._route_segment_distance(
                        route, i, j, distance_matrix
                    )
                    
                    new_route = route[:i+1] + route[i+1:j+1][::-1] + route[j+1:]
                    new_dist = self._route_segment_distance(
                        new_route, i, j, distance_matrix
                    )
                    
                    if new_dist < current_dist:
                        new_time = self._calculate_total_time(new_route, distance_matrix, pois)
                        if new_time <= available_minutes:
                            route = new_route
                            improved = True
                            logger.debug(f"2-opt: improved by {current_dist - new_dist:.2f}km")
        
        if iteration > 1:
            logger.info(f"✓ 2-opt improved route in {iteration} iterations")
        
        return route
    
    def _route_segment_distance(
        self,
        route: List[int],
        start_idx: int,
        end_idx: int,
        distance_matrix: np.ndarray
    ) -> float:
        total = 0.0
        
        if start_idx == 0:
            total += distance_matrix[0][route[start_idx] + 1]
        else:
            total += distance_matrix[route[start_idx - 1] + 1][route[start_idx] + 1]
        
        for k in range(start_idx, min(end_idx, len(route) - 1)):
            total += distance_matrix[route[k] + 1][route[k + 1] + 1]
        
        return total
    
    def _calculate_total_time(
        self,
        route: List[int],
        distance_matrix: np.ndarray,
        pois: List[POI]
    ) -> int:
        total_time = 0
        prev_idx = -1
        
        for poi_idx in route:
            dist = distance_matrix[prev_idx + 1][poi_idx + 1]
            walk_time = self.calculate_walk_time_minutes(dist)
            poi_time = pois[poi_idx].avg_visit_minutes
            total_time += walk_time + poi_time
            prev_idx = poi_idx
        
        return total_time
    
    async def _optimize_route_haversine(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[POI],
        available_hours: float
    ) -> Tuple[List[POI], float]:
        available_minutes = available_hours * 60
        
        current_pos = (start_lat, start_lon)
        remaining_pois = list(pois)
        ordered_route = []
        total_time = 0
        total_distance = 0.0
        
        while remaining_pois and total_time < available_minutes:
            nearest_poi = None
            nearest_dist = float('inf')
            
            for poi in remaining_pois:
                dist = twogis_client.calculate_distance(
                    current_pos[0], current_pos[1],
                    poi.lat, poi.lon
                )
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_poi = poi
            
            if nearest_poi is None:
                break
            
            walk_time = self.calculate_walk_time_minutes(nearest_dist)
            poi_time = nearest_poi.avg_visit_minutes
            
            if total_time + walk_time + poi_time > available_minutes:
                break
            
            ordered_route.append(nearest_poi)
            total_time += walk_time + poi_time
            total_distance += nearest_dist
            current_pos = (nearest_poi.lat, nearest_poi.lon)
            remaining_pois.remove(nearest_poi)
        
        return ordered_route, total_distance
    
    async def insert_smart_coffee_breaks(
        self,
        route: List[POI],
        interval_minutes: int,
        preferences: Dict[str, Any],
        coffee_service: "CoffeeService",
        session: Any = None
    ) -> List[POI]:
        if not route or len(route) < 2:
            return route
        
        result = []
        time_since_last_break = 0
        coffee_added = False
        
        for i, poi in enumerate(route):
            result.append(poi)
            time_since_last_break += poi.avg_visit_minutes
            
            # Add coffee break if:
            # 1. Time threshold reached, OR
            # 2. It's the middle of the route and no coffee added yet
            should_add_coffee = (
                time_since_last_break >= interval_minutes or
                (i == len(route) // 2 and not coffee_added and len(route) > 3)
            )
            
            if should_add_coffee and i < len(route) - 1:
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
                        coffee_added = True
                        logger.info(f"✓ Added coffee break: {cafe_poi.name}")
        
        # If no coffee was added but user wanted coffee, try to add at least one
        if not coffee_added and len(route) >= 2:
            mid_idx = len(route) // 2
            if mid_idx < len(route) - 1:
                logger.info("No coffee break added by interval, adding one in the middle")
                
                cafe_data = await coffee_service.find_best_cafe_for_route(
                    from_poi=route[mid_idx],
                    to_poi=route[mid_idx + 1],
                    preferences=preferences,
                    session=session
                )
                
                if cafe_data:
                    cafe_poi = coffee_service.convert_to_poi(cafe_data)
                    # Insert in the middle
                    result.insert(mid_idx + 1, cafe_poi)
                    logger.info(f"✓ Added guaranteed coffee break: {cafe_poi.name}")
        
        return result


route_planner = RoutePlanner()