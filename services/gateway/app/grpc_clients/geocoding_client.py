import grpc
import logging
import os
from typing import Optional, Tuple, List

from app.proto import geocoding_pb2, geocoding_pb2_grpc

logger = logging.getLogger(__name__)


class GeocodingClient:
    def __init__(self):
        self.host = os.getenv('GEOCODING_SERVICE_HOST', 'localhost')
        self.port = os.getenv('GEOCODING_SERVICE_PORT', '50054')
        self.channel = None
        self.stub = None
    
    async def connect(self):
        self.channel = grpc.aio.insecure_channel(f'{self.host}:{self.port}')
        self.stub = geocoding_pb2_grpc.GeocodingServiceStub(self.channel)
        logger.info(f"✓ Geocoding client connected to {self.host}:{self.port}")
    
    async def close(self):
        if self.channel:
            await self.channel.close()
    
    async def geocode(
        self,
        address: str,
        hint: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
        try:
            request = geocoding_pb2.GeocodeRequest(address=address)
            
            if hint:
                request.hint.lat = hint[0]
                request.hint.lon = hint[1]
            
            response = await self.stub.Geocode(request, timeout=10.0)
            
            if response.success:
                return (response.location.lat, response.location.lon)
            else:
                logger.warning(f"Geocoding failed: {response.error}")
                return None
        
        except grpc.RpcError as e:
            logger.error(f"Geocoding error: {e.code()} - {e.details()}")
            return None
    
    async def reverse_geocode(
        self,
        lat: float,
        lon: float
    ) -> Optional[str]:
        try:
            request = geocoding_pb2.ReverseGeocodeRequest(
                location=geocoding_pb2.Location(lat=lat, lon=lon)
            )
            
            response = await self.stub.ReverseGeocode(request, timeout=10.0)
            return response.address if response.address != "Unknown" else None
        
        except grpc.RpcError as e:
            logger.error(f"Reverse geocoding error: {e.code()} - {e.details()}")
            return None
    
    async def search_cafes(
        self,
        lat: float,
        lon: float,
        radius_km: float = 0.5,
        limit: int = 10
    ) -> List[dict]:
        try:
            request = geocoding_pb2.CafeSearchRequest(
                location=geocoding_pb2.Location(lat=lat, lon=lon),
                radius_km=radius_km,
                limit=limit
            )
            
            response = await self.stub.SearchCafes(request, timeout=15.0)
            
            return [
                {
                    "id": cafe.id,
                    "name": cafe.name,
                    "lat": cafe.location.lat,
                    "lon": cafe.location.lon,
                    "address": cafe.address,
                    "rubrics": list(cafe.rubrics),
                    "rating": cafe.rating
                }
                for cafe in response.cafes
            ]
        
        except grpc.RpcError as e:
            logger.error(f"Cafe search error: {e.code()} - {e.details()}")
            return []
    
    async def health_check(self) -> bool:
        try:
            request = geocoding_pb2.HealthCheckRequest()
            response = await self.stub.HealthCheck(request, timeout=5.0)
            return response.healthy
        except:
            return False


geocoding_client = GeocodingClient()