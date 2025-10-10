import hashlib
import json
import logging
from typing import Optional, Tuple
import httpx
import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeocodingService:
    BASE_URL = "https://nominatim.openstreetmap.org"
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
            logger.info("Geocoding service: Redis connected")
    
    def _get_cache_key(self, address: str) -> str:
        normalized = address.lower().strip()
        return f"geocode:{hashlib.sha256(normalized.encode()).hexdigest()}"
    
    async def _get_cached_coords(self, address: str) -> Optional[Tuple[float, float]]:
        """Get cached geocoding result"""
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(address)
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            data = json.loads(cached)
            logger.info(f"Geocoding cache hit: {address}")
            return (data["lat"], data["lon"])
        
        return None
    
    async def _cache_coords(self, address: str, lat: float, lon: float) -> None:
        """Cache geocoding result"""
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(address)
        data = json.dumps({"lat": lat, "lon": lon})
        
        await self.redis_client.set(
            cache_key,
            data,
            ex=settings.GEOCODING_CACHE_TTL_SECONDS
        )
        logger.info(f"Geocoding cached: {address}")
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True
    )
    async def _fetch_coordinates(self, address: str) -> Optional[Tuple[float, float]]:
        """Fetch coordinates from Nominatim API with retry logic"""
        query = f"{address}, Нижний Новгород, Россия"
        
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 1,
                        "accept-language": "ru"
                    },
                    headers={
                        "User-Agent": "AI-Tourist/1.0 (contact@aitourist.app)"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        lat = float(data[0]["lat"])
                        lon = float(data[0]["lon"])
                        logger.info(f"Geocoding success: {address} -> ({lat}, {lon})")
                        return (lat, lon)
                    else:
                        logger.warning(f"Geocoding: no results for {address}")
                else:
                    logger.error(f"Geocoding API error: {response.status_code}")
                    
            except httpx.TimeoutException:
                logger.error(f"Geocoding timeout for {address}")
                raise
            except Exception as e:
                logger.error(f"Geocoding error for {address}: {str(e)}")
                raise
        
        return None
    
    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address to coordinates with caching
        
        Args:
            address: Street address or location name
            
        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        if not address or not address.strip():
            logger.warning("Empty address provided")
            return None
        
        cached = await self._get_cached_coords(address)
        if cached:
            return cached
        
        coords = await self._fetch_coordinates(address)
        
        if coords:
            await self._cache_coords(address, coords[0], coords[1])
        
        return coords
    
    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Convert coordinates to address (not cached as rarely used)"""
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/reverse",
                    params={
                        "lat": lat,
                        "lon": lon,
                        "format": "json",
                        "addressdetails": 1,
                        "accept-language": "ru"
                    },
                    headers={
                        "User-Agent": "AI-Tourist/1.0 (contact@aitourist.app)"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("display_name", "")
                    
            except Exception as e:
                logger.error(f"Reverse geocoding error: {str(e)}")
        
        return None
    
    async def validate_coordinates(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within Nizhny Novgorod bounds"""
        return (56.29 <= lat <= 56.36) and (43.85 <= lon <= 44.10)


geocoding_service = GeocodingService()