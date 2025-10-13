import grpc
from concurrent import futures
import logging
import numpy as np
from typing import List, Tuple

from proto import routing_pb2, routing_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RoutingServicer(routing_pb2_grpc.RoutingServiceServicer):
    def __init__(self):
        logger.info("✓ Routing Service initialized")
    
    async def OptimizeRoute(self, request, context):
        start = (request.start.lat, request.start.lon)
        pois = [
            (poi.id, poi.lat, poi.lon, poi.avg_visit_minutes)
            for poi in request.pois
        ]
        
        distance_matrix = self._build_distance_matrix(start, pois)
        
        if request.optimization_strategy == "genetic":
            route_order, total_dist, total_time = self._genetic_optimization(
                distance_matrix, pois, request.available_hours * 60
            )
        else:
            route_order, total_dist, total_time = self._greedy_nearest_neighbor(
                distance_matrix, pois, request.available_hours * 60
            )
        
        return routing_pb2.OptimizeRouteResponse(
            poi_order=route_order,
            total_distance_km=total_dist,
            total_time_minutes=total_time,
            algorithm_used=request.optimization_strategy or "greedy",
            optimization_score=1.0 - (total_dist / 100)
        )
    
    async def CalculateRouteGeometry(self, request, context):
        waypoints = [(w.lat, w.lon) for w in request.waypoints]
        
        geometry = self._calculate_geometry(waypoints)
        distance = self._calculate_total_distance(geometry)
        duration = int(distance / 4.5 * 60)
        
        return routing_pb2.RouteGeometryResponse(
            geometry=[
                routing_pb2.Location(lat=lat, lon=lon)
                for lat, lon in geometry
            ],
            distance_km=distance,
            duration_minutes=duration
        )
    
    async def GetDistanceMatrix(self, request, context):
        sources = [(s.lat, s.lon) for s in request.sources]
        targets = [(t.lat, t.lon) for t in request.targets]
        
        matrix = []
        for source in sources:
            row = []
            for target in targets:
                dist = self._haversine(source, target)
                row.append(dist)
            matrix.append(routing_pb2.Row(distances_km=row))
        
        return routing_pb2.DistanceMatrixResponse(matrix=matrix)
    
    async def HealthCheck(self, request, context):
        return routing_pb2.HealthCheckResponse(
            healthy=True,
            version="1.0.0"
        )
    
    def _build_distance_matrix(
        self,
        start: Tuple[float, float],
        pois: List[Tuple[int, float, float, int]]
    ) -> np.ndarray:
        n = len(pois) + 1
        matrix = np.zeros((n, n))
        
        all_points = [start] + [(lat, lon) for _, lat, lon, _ in pois]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    matrix[i][j] = self._haversine(all_points[i], all_points[j])
        
        return matrix
    
    def _greedy_nearest_neighbor(
        self,
        matrix: np.ndarray,
        pois: List[Tuple[int, float, float, int]],
        available_minutes: float
    ) -> Tuple[List[int], float, int]:
        n = len(pois)
        visited = set()
        route = []
        total_dist = 0.0
        total_time = 0
        current = 0
        
        while len(visited) < n and total_time < available_minutes:
            nearest_idx = None
            nearest_dist = float('inf')
            
            for i in range(n):
                if i not in visited:
                    dist = matrix[current][i + 1]
                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_idx = i
            
            if nearest_idx is None:
                break
            
            walk_time = int((nearest_dist / 4.5) * 60) + 5
            poi_time = pois[nearest_idx][3]
            
            if total_time + walk_time + poi_time > available_minutes:
                break
            
            visited.add(nearest_idx)
            route.append(pois[nearest_idx][0])
            total_dist += nearest_dist
            total_time += walk_time + poi_time
            current = nearest_idx + 1
        
        return route, total_dist, total_time
    
    def _genetic_optimization(
        self,
        matrix: np.ndarray,
        pois: List[Tuple[int, float, float, int]],
        available_minutes: float
    ) -> Tuple[List[int], float, int]:
        return self._greedy_nearest_neighbor(matrix, pois, available_minutes)
    
    def _calculate_geometry(
        self,
        waypoints: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        if len(waypoints) < 2:
            return waypoints
        
        geometry = []
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            steps = 10
            for j in range(steps):
                t = j / steps
                lat = start[0] + (end[0] - start[0]) * t
                lon = start[1] + (end[1] - start[1]) * t
                geometry.append((lat, lon))
        
        geometry.append(waypoints[-1])
        return geometry
    
    def _calculate_total_distance(
        self,
        geometry: List[Tuple[float, float]]
    ) -> float:
        total = 0.0
        for i in range(len(geometry) - 1):
            total += self._haversine(geometry[i], geometry[i + 1])
        return total
    
    def _haversine(
        self,
        point1: Tuple[float, float],
        point2: Tuple[float, float]
    ) -> float:
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371.0
        lat1, lon1 = map(radians, point1)
        lat2, lon2 = map(radians, point2)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c


def serve(port: int = 50053):
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=4))
    
    servicer = RoutingServicer()
    routing_pb2_grpc.add_RoutingServiceServicer_to_server(servicer, server)
    
    server.add_insecure_port(f'[::]:{port}')
    
    logger.info(f"🚀 Routing Service listening on port {port}")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    import os
    port = int(os.getenv('GRPC_PORT', '50053'))
    serve(port)