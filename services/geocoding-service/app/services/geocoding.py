import logging
from typing import Optional, Tuple

import grpc

from app.proto import geocoding_pb2, geocoding_pb2_grpc
from app.services.twogis_client import twogis_client

logger = logging.getLogger(__name__)


class GeocodingService:
    """Geocoding utilities mirroring the monolith implementation."""

    NIZHNY_NOVGOROD_BOUNDS = {
        "lat_min": 56.20,
        "lat_max": 56.40,
        "lon_min": 43.75,
        "lon_max": 44.15,
    }

    async def geocode_address(
        self, address: str, hint_location: Optional[Tuple[float, float]] = None
    ) -> Optional[Tuple[float, float]]:
        if not address or not address.strip():
            logger.warning("Empty address provided")
            return None

        coords = await twogis_client.geocode(address, location=hint_location)
        if coords and self.validate_coordinates(*coords):
            return coords

        if coords:
            logger.warning(
                "Geocoded coordinates %s are outside Nizhny Novgorod bounds", coords
            )
        return None

    async def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        if not self.validate_coordinates(lat, lon):
            return None
        return await twogis_client.reverse_geocode(lat, lon)

    def validate_coordinates(self, lat: float, lon: float) -> bool:
        return (
            self.NIZHNY_NOVGOROD_BOUNDS["lat_min"] <= lat <= self.NIZHNY_NOVGOROD_BOUNDS["lat_max"]
            and self.NIZHNY_NOVGOROD_BOUNDS["lon_min"] <= lon <= self.NIZHNY_NOVGOROD_BOUNDS["lon_max"]
        )


geocoding_service = GeocodingService()


class GeocodingServicer(geocoding_pb2_grpc.GeocodingServiceServicer):
    """gRPC servicer exposing the geocoding operations."""

    def __init__(self, service: Optional[GeocodingService] = None) -> None:
        self.service = service or geocoding_service

    async def initialize(self) -> None:
        await twogis_client.connect_redis()
        logger.info("✓ Geocoding Service initialized")
        logger.info(
            "Nizhny Novgorod bounds: lat[%s, %s], lon[%s, %s]",
            self.service.NIZHNY_NOVGOROD_BOUNDS["lat_min"],
            self.service.NIZHNY_NOVGOROD_BOUNDS["lat_max"],
            self.service.NIZHNY_NOVGOROD_BOUNDS["lon_min"],
            self.service.NIZHNY_NOVGOROD_BOUNDS["lon_max"],
        )

    async def GeocodeAddress(  # noqa: N802 (gRPC naming)
        self, request: geocoding_pb2.GeocodeRequest, context
    ) -> geocoding_pb2.GeocodeResponse:
        query = request.address.strip()
        if request.city:
            query = f"{query}, {request.city}".strip(", ")

        try:
            coords = await self.service.geocode_address(query)
            if not coords:
                return geocoding_pb2.GeocodeResponse(success=False)

            formatted = await self.service.reverse_geocode(*coords)
            return geocoding_pb2.GeocodeResponse(
                success=True,
                lat=coords[0],
                lon=coords[1],
                formatted_address=formatted or query,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Geocoding failed: %s", exc)
            if context is not None:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(f"Geocoding failed: {exc}")
            return geocoding_pb2.GeocodeResponse(success=False)

    async def ValidateCoordinates(  # noqa: N802 (gRPC naming)
        self, request: geocoding_pb2.CoordinateValidationRequest, context
    ) -> geocoding_pb2.CoordinateValidationResponse:
        is_valid = self.service.validate_coordinates(request.lat, request.lon)
        reason = (
            "Coordinates are valid"
            if is_valid
            else "Coordinates are outside Nizhny Novgorod bounds"
        )
        return geocoding_pb2.CoordinateValidationResponse(valid=is_valid, reason=reason)


__all__ = ["GeocodingService", "GeocodingServicer", "geocoding_service"]
