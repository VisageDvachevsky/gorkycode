from __future__ import annotations

from typing import Optional, Tuple

from app.grpc.clients import grpc_clients
from app.models.schemas import RouteRequest

from .exceptions import ExternalServiceError, RoutePlanningError


async def resolve_start_location(request: RouteRequest) -> Tuple[float, float, str]:
    lat: Optional[float] = request.start_lat
    lon: Optional[float] = request.start_lon
    label = request.start_address or "Заданная точка старта"

    if lat is None or lon is None:
        if not request.start_address:
            raise RoutePlanningError(
                "Необходимо указать адрес или координаты старта", status_code=400
            )
        try:
            geocode = await grpc_clients.geocoding_client.geocode_address(request.start_address)
        except Exception as exc:
            raise ExternalServiceError("Сервис геокодинга недоступен") from exc

        if not geocode.success:
            raise RoutePlanningError("Не удалось распознать адрес старта", status_code=400)

        lat = geocode.lat
        lon = geocode.lon
        label = geocode.formatted_address or request.start_address

    try:
        validation = await grpc_clients.geocoding_client.validate_coordinates(lat, lon)
    except Exception as exc:
        raise ExternalServiceError("Сервис геокодинга недоступен") from exc

    if not validation.valid:
        raise RoutePlanningError(validation.reason or "Старт вне доступной зоны", status_code=400)

    return float(lat), float(lon), label
