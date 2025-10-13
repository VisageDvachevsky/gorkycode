import grpc
from concurrent import futures
import logging
import httpx
import os
from typing import Optional, Tuple

from proto import geocoding_pb2, geocoding_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeocodingServicer(geocoding_pb2_grpc.GeocodingServiceServicer):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://catalog.api.2gis.com/3.0/items"
        logger.info("✓ Geocoding Service initialized")
    
    async def Geocode(self, request, context):
        try:
            coords = await self._geocode_address(
                request.address,
                (request.hint.lat, request.hint.lon) if request.HasField('hint') else None
            )
            
            if coords:
                return geocoding_pb2.GeocodeResponse(
                    success=True,
                    location=geocoding_pb2.Location(lat=coords[0], lon=coords[1])
                )
            else:
                return geocoding_pb2.GeocodeResponse(
                    success=False,
                    error="Address not found"
                )
        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return geocoding_pb2.GeocodeResponse(
                success=False,
                error=str(e)
            )
    
    async def ReverseGeocode(self, request, context):
        try:
            address = await self._reverse_geocode(
                request.location.lat,
                request.location.lon
            )
            return geocoding_pb2.ReverseGeocodeResponse(address=address or "Unknown")
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return geocoding_pb2.ReverseGeocodeResponse(address="Unknown")
    
    async def SearchCafes(self, request, context):
        try:
            cafes = await self._search_cafes(
                (request.location.lat, request.location.lon),
                request.radius_km,
                request.limit,
                request.filters
            )
            
            return geocoding_pb2.CafeSearchResponse(
                cafes=[
                    geocoding_pb2.Cafe(
                        id=cafe["id"],
                        name=cafe["name"],
                        location=geocoding_pb2.Location(
                            lat=cafe["lat"],
                            lon=cafe["lon"]
                        ),
                        address=cafe.get("address", ""),
                        rubrics=cafe.get("rubrics", []),
                        rating=cafe.get("rating", 0.0)
                    )
                    for cafe in cafes
                ]
            )
        except Exception as e:
            logger.error(f"Cafe search error: {e}")
            return geocoding_pb2.CafeSearchResponse(cafes=[])
    
    async def GetWalkingRoute(self, request, context):
        waypoints = [(w.lat, w.lon) for w in request.waypoints]
        
        geometry = self._calculate_simple_geometry(waypoints)
        distance = self._calculate_distance(geometry)
        duration = int(distance / 4.5 * 60)
        
        return geocoding_pb2.WalkingRouteResponse(
            geometry=[
                geocoding_pb2.Location(lat=lat, lon=lon)
                for lat, lon in geometry
            ],
            distance_km=distance,
            duration_minutes=duration
        )
    
    async def HealthCheck(self, request, context):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    self.base_url,
                    params={"key": self.api_key, "q": "test"}
                )
                api_valid = response.status_code == 200
        except:
            api_valid = False
        
        return geocoding_pb2.HealthCheckResponse(
            healthy=True,
            api_key_valid=api_valid,
            requests_today=0
        )
    
    async def _geocode_address(
        self,
        address: str,
        hint: Optional[Tuple[float, float]]
    ) -> Optional[Tuple[float, float]]:
        async with httpx.AsyncClient(timeout=10) as client:
            params = {
                "key": self.api_key,
                "q": f"{address}, Нижний Новгород",
                "fields": "items.point",
                "page_size": 1
            }
            
            if hint:
                params["location"] = f"{hint[1]},{hint[0]}"
            
            response = await client.get(self.base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("result", {}).get("items", [])
                if items and "point" in items[0]:
                    point = items[0]["point"]
                    return (point["lat"], point["lon"])
        
        return None
    
    async def _reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        async with httpx.AsyncClient(timeout=10) as client:
            params = {
                "key": self.api_key,
                "lat": lat,
                "lon": lon,
                "fields": "items.full_name",
                "page_size": 1
            }
            
            response = await client.get(
                "https://catalog.api.2gis.com/3.0/items/geocode",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("result", {}).get("items", [])
                if items:
                    return items[0].get("full_name", "")
        
        return None
    
    async def _search_cafes(
        self,
        location: Tuple[float, float],
        radius_km: float,
        limit: int,
        filters
    ) -> list:
        async with httpx.AsyncClient(timeout=10) as client:
            params = {
                "key": self.api_key,
                "rubric_id": "162,164",
                "point": f"{location[1]},{location[0]}",
                "radius": int(radius_km * 1000),
                "sort": "rating",
                "fields": "items.point,items.address_name,items.rubrics",
                "page_size": min(limit, 20)
            }
            
            response = await client.get(self.base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("result", {}).get("items", [])
                
                cafes = []
                for item in items:
                    point = item.get("point", {})
                    if not point or "lat" not in point:
                        continue
                    
                    cafes.append({
                        "id": str(item.get("id", "")),
                        "name": item.get("name", "Кафе"),
                        "lat": point["lat"],
                        "lon": point["lon"],
                        "address": item.get("address_name", ""),
                        "rubrics": [r.get("name", "") for r in item.get("rubrics", [])],
                        "rating": 4.0
                    })
                
                return cafes
        
        return []
    
    def _calculate_simple_geometry(
        self,
        waypoints: list[Tuple[float, float]]
    ) -> list[Tuple[float, float]]:
        if len(waypoints) < 2:
            return waypoints
        
        geometry = []
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            for j in range(10):
                t = j / 10
                lat = start[0] + (end[0] - start[0]) * t
                lon = start[1] + (end[1] - start[1]) * t
                geometry.append((lat, lon))
        
        geometry.append(waypoints[-1])
        return geometry
    
    def _calculate_distance(self, geometry: list[Tuple[float, float]]) -> float:
        from math import radians, sin, cos, sqrt, atan2
        
        total = 0.0
        R = 6371.0
        
        for i in range(len(geometry) - 1):
            lat1, lon1 = map(radians, geometry[i])
            lat2, lon2 = map(radians, geometry[i + 1])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            total += R * c
        
        return total


def serve(api_key: str, port: int = 50054):
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=4))
    
    servicer = GeocodingServicer(api_key)
    geocoding_pb2_grpc.add_GeocodingServiceServicer_to_server(servicer, server)
    
    server.add_insecure_port(f'[::]:{port}')
    
    logger.info(f"🚀 Geocoding Service listening on port {port}")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    api_key = os.getenv('TWOGIS_API_KEY')
    if not api_key:
        raise ValueError("TWOGIS_API_KEY required")
    
    port = int(os.getenv('GRPC_PORT', '50054'))
    serve(api_key, port)