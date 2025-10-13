import grpc
import logging
import os
from typing import List, Tuple

from app.proto import routing_pb2, routing_pb2_grpc

logger = logging.getLogger(__name__)


class RoutingClient:
    def __init__(self):
        self.host = os.getenv('ROUTING_SERVICE_HOST', 'localhost')
        self.port = os.getenv('ROUTING_SERVICE_PORT', '50053')
        self.channel = None
        self.stub = None
    
    async def connect(self):
        self.channel = grpc.aio.insecure_channel(f'{self.host}:{self.port}')
        self.stub = routing_pb2_grpc.RoutingServiceStub(self.channel)
        logger.info(f"✓ Routing client connected to {self.host}:{self.port}")
    
    async def close(self):
        if self.channel:
            await self.channel.close()
    
    async def optimize_route(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[dict],
        available_hours: float
    ) -> Tuple[List[int], float, int]:
        try:
            request = routing_pb2.OptimizeRouteRequest(
                start=routing_pb2.Location(lat=start_lat, lon=start_lon),
                pois=[
                    routing_pb2.POILocation(
                        id=poi["id"],
                        lat=poi["lat"],
                        lon=poi["lon"],
                        avg_visit_minutes=poi.get("avg_visit_minutes", 30)
                    )
                    for poi in pois
                ],
                available_hours=available_hours,
                optimization_strategy="greedy"
            )
            
            response = await self.stub.OptimizeRoute(request, timeout=30.0)
            
            return (
                list(response.poi_order),
                response.total_distance_km,
                response.total_time_minutes
            )
        
        except grpc.RpcError as e:
            logger.error(f"Routing optimization error: {e.code()} - {e.details()}")
            raise
    
    async def calculate_geometry(
        self,
        waypoints: List[Tuple[float, float]]
    ) -> List[Tuple[float, float]]:
        try:
            request = routing_pb2.RouteGeometryRequest(
                waypoints=[
                    routing_pb2.Location(lat=lat, lon=lon)
                    for lat, lon in waypoints
                ],
                transport_type="pedestrian"
            )
            
            response = await self.stub.CalculateRouteGeometry(request, timeout=20.0)
            
            return [(loc.lat, loc.lon) for loc in response.geometry]
        
        except grpc.RpcError as e:
            logger.error(f"Geometry calculation error: {e.code()} - {e.details()}")
            raise
    
    async def health_check(self) -> bool:
        try:
            request = routing_pb2.HealthCheckRequest()
            response = await self.stub.HealthCheck(request, timeout=5.0)
            return response.healthy
        except:
            return False


routing_client = RoutingClient()