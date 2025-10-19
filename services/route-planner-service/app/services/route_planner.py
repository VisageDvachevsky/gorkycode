import logging
from typing import List, Tuple

import grpc
import numpy as np
from geopy.distance import geodesic

from app.proto import route_pb2, route_pb2_grpc
from app.core.config import settings

logger = logging.getLogger(__name__)


class RoutePlannerServicer(route_pb2_grpc.RoutePlannerServiceServicer):
    def __init__(self):
        self.walk_speed_kmh = settings.WALK_SPEED_KMH

    async def initialize(self):
        """Initialize service"""
        logger.info("✓ Route Planner Service initialized")
    
    async def OptimizeRoute(
        self,
        request: route_pb2.RouteOptimizationRequest,
        context
    ) -> route_pb2.RouteOptimizationResponse:
        """Optimize route using nearest neighbor algorithm"""
        try:
            pois = list(request.pois)
            
            if not pois:
                return route_pb2.RouteOptimizationResponse(
                    optimized_route=[],
                    total_distance_km=0.0,
                    total_minutes=0
                )
            
            start_point = (request.start_lat, request.start_lon)
            available_minutes = request.available_hours * 60
            
            distance_matrix = self._calculate_distance_matrix(start_point, pois)
            
            route_indices, total_minutes, total_distance = self._nearest_neighbor_route(
                distance_matrix=distance_matrix,
                pois=pois,
                available_minutes=available_minutes
            )
            
            optimized_route = [pois[idx] for idx in route_indices]
            
            logger.info(f"Optimized route: {len(optimized_route)} POIs, {total_distance:.2f}km")
            
            return route_pb2.RouteOptimizationResponse(
                optimized_route=optimized_route,
                total_distance_km=total_distance,
                total_minutes=int(total_minutes)
            )
            
        except Exception as e:
            logger.error(f"Route optimization failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Route optimization failed: {str(e)}")
            return route_pb2.RouteOptimizationResponse()
    
    async def CalculateRouteGeometry(
        self,
        request: route_pb2.RouteGeometryRequest,
        context
    ) -> route_pb2.RouteGeometryResponse:
        """Calculate route geometry (simplified - just waypoints)"""
        try:
            geometry = [
                route_pb2.Coordinate(lat=request.start_lat, lon=request.start_lon)
            ]
            
            for waypoint in request.waypoints:
                geometry.append(waypoint)
            
            total_distance = 0.0
            for i in range(len(geometry) - 1):
                dist = geodesic(
                    (geometry[i].lat, geometry[i].lon),
                    (geometry[i+1].lat, geometry[i+1].lon)
                ).km
                total_distance += dist
            
            return route_pb2.RouteGeometryResponse(
                geometry=geometry,
                total_distance_km=total_distance
            )
            
        except Exception as e:
            logger.error(f"Geometry calculation failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Geometry calculation failed: {str(e)}")
            return route_pb2.RouteGeometryResponse()
    
    def _calculate_distance_matrix(
        self,
        start_point: Tuple[float, float],
        pois: List[route_pb2.POIInfo]
    ) -> np.ndarray:
        """Calculate distance matrix between all points"""
        n = len(pois) + 1
        matrix = np.zeros((n, n))
        
        points = [start_point] + [(poi.lat, poi.lon) for poi in pois]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = geodesic(points[i], points[j]).km
        
        return matrix
    
    def _nearest_neighbor_route(
        self,
        distance_matrix: np.ndarray,
        pois: List[route_pb2.POIInfo],
        available_minutes: float
    ) -> Tuple[List[int], float, float]:
        """Greedy nearest neighbor algorithm"""
        route = []
        remaining = set(range(len(pois)))
        current_idx = -1
        total_time = 0.0
        total_distance = 0.0
        
        while remaining:
            best_idx = None
            best_score = float('inf')
            
            for poi_idx in remaining:
                dist = distance_matrix[current_idx + 1][poi_idx + 1]
                walk_time = self._calculate_walk_time_minutes(dist)
                poi_time = pois[poi_idx].avg_visit_minutes
                
                score = dist
                
                if score < best_score:
                    potential_time = total_time + walk_time + poi_time
                    if potential_time <= available_minutes:
                        best_score = score
                        best_idx = poi_idx
            
            if best_idx is None:
                break
            
            nearest_dist = distance_matrix[current_idx + 1][best_idx + 1]
            walk_time = self._calculate_walk_time_minutes(nearest_dist)
            poi_time = pois[best_idx].avg_visit_minutes
            
            route.append(best_idx)
            total_time += walk_time + poi_time
            total_distance += nearest_dist
            current_idx = best_idx
            remaining.remove(best_idx)
        
        return route, total_time, total_distance
    
    def _calculate_walk_time_minutes(self, distance_km: float) -> float:
        """Calculate walking time in minutes"""
        return (distance_km / self.walk_speed_kmh) * 60