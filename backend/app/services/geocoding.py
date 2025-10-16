import logging
from typing import Optional, Tuple

from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


class GeocodingService:
    """Geocoding service using 2GIS Places + Geocoding APIs"""
    
    NIZHNY_NOVGOROD_BOUNDS = {
        "lat_min": 56.20,  # Expanded south
        "lat_max": 56.40,  # Expanded north
        "lon_min": 43.75,  # Expanded west
        "lon_max": 44.15   # Expanded east
    }
    
    async def geocode_address(
        self,
        address: str,
        hint_location: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
        """Convert address OR landmark to coordinates using 2GIS"""
        
        if not address or not address.strip():
            logger.warning("Empty address provided")
            return None
        
        coords = await twogis_client.geocode(address, location=hint_location)
        
        if coords:
            if self.validate_coordinates(coords[0], coords[1]):
                return coords
            else:
                logger.warning(f"Geocoded coordinates {coords} are outside Nizhny Novgorod bounds")
        
        return None
    
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Convert coordinates to address using 2GIS"""
        
        if not self.validate_coordinates(lat, lon):
            return None
        
        return await twogis_client.reverse_geocode(lat, lon)
    
    def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within Nizhny Novgorod bounds"""
        
        return (
            self.NIZHNY_NOVGOROD_BOUNDS["lat_min"] <= lat <= self.NIZHNY_NOVGOROD_BOUNDS["lat_max"] and
            self.NIZHNY_NOVGOROD_BOUNDS["lon_min"] <= lon <= self.NIZHNY_NOVGOROD_BOUNDS["lon_max"]
        )


geocoding_service = GeocodingService()