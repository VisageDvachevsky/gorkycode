import logging

import grpc
import httpx

from app.proto import geocoding_pb2, geocoding_pb2_grpc
from app.core.config import settings

logger = logging.getLogger(__name__)


class GeocodingServicer(geocoding_pb2_grpc.GeocodingServiceServicer):
    def __init__(self):
        self.twogis_api_key = settings.TWOGIS_API_KEY
        self.nn_bounds = {
            "lat_min": settings.NN_LAT_MIN,
            "lat_max": settings.NN_LAT_MAX,
            "lon_min": settings.NN_LON_MIN,
            "lon_max": settings.NN_LON_MAX
        }

    async def initialize(self):
        """Initialize geocoding service"""
        logger.info("✓ Geocoding Service initialized")
        logger.info(f"Nizhny Novgorod bounds: lat[{self.nn_bounds['lat_min']}, {self.nn_bounds['lat_max']}], lon[{self.nn_bounds['lon_min']}, {self.nn_bounds['lon_max']}]")
    
    async def GeocodeAddress(
        self,
        request: geocoding_pb2.GeocodeRequest,
        context
    ) -> geocoding_pb2.GeocodeResponse:
        """Geocode address using 2GIS API"""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "q": f"{request.address}, {request.city}",
                    "key": self.twogis_api_key,
                    "fields": "items.point"
                }
                
                response = await client.get(
                    "https://catalog.api.2gis.com/3.0/items/geocode",
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result", {}).get("items"):
                        item = data["result"]["items"][0]
                        point = item["point"]
                        
                        return geocoding_pb2.GeocodeResponse(
                            success=True,
                            lat=point["lat"],
                            lon=point["lon"],
                            formatted_address=item.get("full_name", request.address)
                        )
            
            return geocoding_pb2.GeocodeResponse(
                success=False,
                lat=0.0,
                lon=0.0,
                formatted_address=""
            )
            
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Geocoding failed: {str(e)}")
            return geocoding_pb2.GeocodeResponse(success=False)
    
    async def ValidateCoordinates(
        self,
        request: geocoding_pb2.CoordinateValidationRequest,
        context
    ) -> geocoding_pb2.CoordinateValidationResponse:
        """Validate coordinates are within Nizhny Novgorod"""
        lat, lon = request.lat, request.lon
        
        if (self.nn_bounds["lat_min"] <= lat <= self.nn_bounds["lat_max"] and
            self.nn_bounds["lon_min"] <= lon <= self.nn_bounds["lon_max"]):
            return geocoding_pb2.CoordinateValidationResponse(
                valid=True,
                reason="Coordinates are valid"
            )
        else:
            return geocoding_pb2.CoordinateValidationResponse(
                valid=False,
                reason="Coordinates are outside Nizhny Novgorod bounds"
            )