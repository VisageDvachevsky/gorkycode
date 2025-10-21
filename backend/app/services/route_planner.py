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
        
        # Smart reordering: prefer starting from furthest point
        pois = self._reorder_pois_by_sectors(start_lat, start_lon, pois)
        
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
    
    def _reorder_pois_by_sectors(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[POI]
    ) -> List[POI]:
        """Reorder POIs to prefer starting from furthest quadrant"""
        
        if len(pois) <= 3:
            return pois
        
        # Calculate center of mass
        center_lat = sum(poi.lat for poi in pois) / len(pois)
        center_lon = sum(poi.lon for poi in pois) / len(pois)
        
        # Assign each POI to a sector (NE, SE, SW, NW)
        sectors = {
            'NE': [], 'SE': [], 'SW': [], 'NW': []
        }
        
        for poi in pois:
            if poi.lat >= center_lat and poi.lon >= center_lon:
                sectors['NE'].append(poi)
            elif poi.lat < center_lat and poi.lon >= center_lon:
                sectors['SE'].append(poi)
            elif poi.lat < center_lat and poi.lon < center_lon:
                sectors['SW'].append(poi)
            else:
                sectors['NW'].append(poi)
        
        # Find which sector start point is in
        start_sector = None
        if start_lat >= center_lat and start_lon >= center_lon:
            start_sector = 'NE'
        elif start_lat < center_lat and start_lon >= center_lon:
            start_sector = 'SE'
        elif start_lat < center_lat and start_lon < center_lon:
            start_sector = 'SW'
        else:
            start_sector = 'NW'
        
        # Prefer POIs from opposite sectors first (to minimize backtracking)
        sector_priority = {
            'NE': ['SW', 'SE', 'NW', 'NE'],
            'SE': ['NW', 'NE', 'SW', 'SE'],
            'SW': ['NE', 'NW', 'SE', 'SW'],
            'NW': ['SE', 'SW', 'NE', 'NW']
        }
        
        reordered = []
        for sector_key in sector_priority.get(start_sector, ['NE', 'SE', 'SW', 'NW']):
            reordered.extend(sectors[sector_key])
        
        if reordered:
            logger.info(f"✓ Reordered POIs by sectors (start: {start_sector})")
            return reordered
        
        return pois
    
    async def _get_real_distance_matrix(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[POI]
    ) -> Optional[np.ndarray]:
        all_points = [(start_lat, start_lon)] + [(poi.lat, poi.lon) for poi in pois]
        
        max_points = 10

        if len(all_points) <= max_points:
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

        logger.info(f"Computing distance matrix in batches: {len(all_points)} points")

        n = len(all_points)
        matrix = np.full((n, n), float("inf"))
        chunk_size = max(2, max_points // 2)

        for src_start in range(0, n, chunk_size):
            src_indices = list(range(src_start, min(n, src_start + chunk_size)))

            for tgt_start in range(0, n, chunk_size):
                tgt_indices = list(range(tgt_start, min(n, tgt_start + chunk_size)))

                union: List[int] = []
                local_index: Dict[int, int] = {}

                for idx in src_indices + tgt_indices:
                    if idx not in local_index:
                        local_index[idx] = len(union)
                        union.append(idx)

                block_points = [all_points[idx] for idx in union]
                block_sources = [local_index[idx] for idx in src_indices]
                block_targets = [local_index[idx] for idx in tgt_indices]

                try:
                    data = await twogis_client.request_distance_matrix(
                        block_points,
                        block_sources,
                        block_targets,
                        transport="pedestrian",
                    )
                except Exception as e:
                    logger.error(
                        f"Distance matrix batch failed ({src_indices}->{tgt_indices}): {e}"
                    )
                    return None

                if not data:
                    logger.warning(
                        f"Distance matrix batch empty ({src_indices}->{tgt_indices}), falling back"
                    )
                    return None

                block_matrix = twogis_client.parse_distance_matrix(
                    data,
                    num_sources=len(block_sources),
                    num_targets=len(block_targets)
                )

                for s_offset, s_idx in enumerate(src_indices):
                    for t_offset, t_idx in enumerate(tgt_indices):
                        value = block_matrix[s_offset][t_offset]
                        if not np.isfinite(value):
                            start = all_points[s_idx]
                            end = all_points[t_idx]
                            value = twogis_client.calculate_distance(
                                start[0], start[1], end[0], end[1]
                            )
                        matrix[s_idx][t_idx] = value

        for i in range(n):
            matrix[i][i] = 0.0

        return matrix
    
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
        prev_direction = None  # Track movement direction
        
        while remaining and total_time < available_minutes:
            best_idx = None
            best_score = float('inf')
            
            for poi_idx in remaining:
                dist = distance_matrix[current_idx + 1][poi_idx + 1]
                
                # Calculate direction-aware score
                score = dist
                
                # Penalty for backtracking
                if current_idx >= 0 and prev_direction is not None:
                    current_pos = (pois[current_idx].lat, pois[current_idx].lon) if current_idx >= 0 else (0, 0)
                    next_pos = (pois[poi_idx].lat, pois[poi_idx].lon)
                    
                    # Calculate direction vector
                    if current_idx >= 0:
                        direction = (
                            next_pos[0] - current_pos[0],
                            next_pos[1] - current_pos[1]
                        )
                        
                        # Dot product with previous direction
                        # Positive = same direction, Negative = backtracking
                        dot = direction[0] * prev_direction[0] + direction[1] * prev_direction[1]
                        
                        if dot < 0:  # Backtracking
                            score *= 1.3  # 30% penalty
                
                if score < best_score:
                    best_score = score
                    best_idx = poi_idx
            
            if best_idx is None:
                break
            
            nearest_dist = distance_matrix[current_idx + 1][best_idx + 1]
            walk_time = self.calculate_walk_time_minutes(nearest_dist)
            poi_time = pois[best_idx].avg_visit_minutes
            
            if total_time + walk_time + poi_time > available_minutes:
                break
            
            # Update direction vector
            if current_idx >= 0:
                current_pos = (pois[current_idx].lat, pois[current_idx].lon)
                next_pos = (pois[best_idx].lat, pois[best_idx].lon)
                prev_direction = (
                    next_pos[0] - current_pos[0],
                    next_pos[1] - current_pos[1]
                )
            
            route.append(best_idx)
            total_time += walk_time + poi_time
            total_distance += nearest_dist
            current_idx = best_idx
            remaining.remove(best_idx)
        
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
        session: Any = None,
        start_time: Optional[datetime] = None
    ) -> List[POI]:
        if not route or len(route) < 2:
            return route
        
        result = []
        time_since_last_break = 0
        coffee_added = False
        
        # Calculate current time if provided
        current_time = start_time if start_time else datetime.now()
        
        for i, poi in enumerate(route):
            result.append(poi)
            
            # Update current time
            current_time += timedelta(minutes=poi.avg_visit_minutes)
            time_since_last_break += poi.avg_visit_minutes
            
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
                    # Check if cafe is open at current_time
                    from app.services.time_scheduler import time_scheduler
                    
                    is_open = time_scheduler.validate_cafe_timing(cafe_data, current_time)
                    
                    if not is_open:
                        logger.warning(
                            f"Skipping {cafe_data['name']} - closed at {current_time.strftime('%H:%M')}"
                        )
                        continue
                    
                    cafe_poi = coffee_service.convert_to_poi(cafe_data)
                    
                    if cafe_poi.id not in [p.id for p in result]:
                        result.append(cafe_poi)
                        time_since_last_break = 0
                        coffee_added = True
                        current_time += timedelta(minutes=cafe_poi.avg_visit_minutes)
                        logger.info(f"✓ Added coffee break: {cafe_poi.name} (open at {current_time.strftime('%H:%M')})")
        
        if not coffee_added and len(route) >= 2:
            logger.info("No coffee break added by interval, trying middle...")
            mid_idx = len(route) // 2
            if mid_idx < len(route) - 1:
                cafe_data = await coffee_service.find_best_cafe_for_route(
                    from_poi=route[mid_idx],
                    to_poi=route[mid_idx + 1],
                    preferences=preferences,
                    session=session
                )
                
                if cafe_data:
                    # Calculate time at middle
                    mid_time = start_time if start_time else datetime.now()
                    for poi in route[:mid_idx+1]:
                        mid_time += timedelta(minutes=poi.avg_visit_minutes)
                    
                    from app.services.time_scheduler import time_scheduler
                    is_open = time_scheduler.validate_cafe_timing(cafe_data, mid_time)
                    
                    if is_open:
                        cafe_poi = coffee_service.convert_to_poi(cafe_data)
                        result.insert(mid_idx + 1, cafe_poi)
                        logger.info(f"✓ Added guaranteed coffee break: {cafe_poi.name}")
                    else:
                        logger.warning(f"Middle cafe {cafe_data['name']} closed at {mid_time.strftime('%H:%M')}")
        
        return result

route_planner = RoutePlanner()