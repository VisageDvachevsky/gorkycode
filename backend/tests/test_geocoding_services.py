import math
from typing import List
from unittest.mock import AsyncMock

import pytest

from app.services import geocoding as geocoding_module
from app.services.geocoding import GeocodingService
from app.services.twogis_client import TwoGISClient


@pytest.fixture
def geocoding_service() -> GeocodingService:
    return GeocodingService()


@pytest.mark.asyncio
async def test_geocode_address_returns_coordinates_when_valid(monkeypatch, geocoding_service: GeocodingService) -> None:
    expected = (56.25, 43.95)
    mock_geocode = AsyncMock(return_value=expected)
    monkeypatch.setattr(geocoding_module.twogis_client, "geocode", mock_geocode)

    coords = await geocoding_service.geocode_address("Нижегородский кремль")

    assert coords == expected
    mock_geocode.assert_awaited_once_with("Нижегородский кремль", location=None)


@pytest.mark.asyncio
async def test_geocode_address_rejects_out_of_bounds(monkeypatch, geocoding_service: GeocodingService) -> None:
    mock_geocode = AsyncMock(return_value=(55.75, 37.61))  # Moscow
    monkeypatch.setattr(geocoding_module.twogis_client, "geocode", mock_geocode)

    coords = await geocoding_service.geocode_address("Красная площадь")

    assert coords is None
    mock_geocode.assert_awaited_once()


@pytest.mark.asyncio
async def test_geocode_address_ignores_empty_input(monkeypatch, geocoding_service: GeocodingService) -> None:
    mock_geocode = AsyncMock()
    monkeypatch.setattr(geocoding_module.twogis_client, "geocode", mock_geocode)

    assert await geocoding_service.geocode_address("   ") is None
    mock_geocode.assert_not_called()


@pytest.mark.asyncio
async def test_reverse_geocode_returns_address(monkeypatch, geocoding_service: GeocodingService) -> None:
    expected_address = "Нижний Новгород, Кремль"
    mock_reverse = AsyncMock(return_value=expected_address)
    monkeypatch.setattr(geocoding_module.twogis_client, "reverse_geocode", mock_reverse)

    result = await geocoding_service.reverse_geocode(56.3269, 44.0073)

    assert result == expected_address
    mock_reverse.assert_awaited_once_with(56.3269, 44.0073)


@pytest.mark.asyncio
async def test_reverse_geocode_rejects_invalid_coordinates(monkeypatch, geocoding_service: GeocodingService) -> None:
    mock_reverse = AsyncMock()
    monkeypatch.setattr(geocoding_module.twogis_client, "reverse_geocode", mock_reverse)

    assert await geocoding_service.reverse_geocode(0.0, 0.0) is None
    mock_reverse.assert_not_called()


def test_validate_coordinates_in_bounds(geocoding_service: GeocodingService) -> None:
    assert geocoding_service.validate_coordinates(56.33, 43.99)


def test_validate_coordinates_out_of_bounds(geocoding_service: GeocodingService) -> None:
    assert not geocoding_service.validate_coordinates(55.0, 32.0)


@pytest.mark.asyncio
async def test_twogis_client_uses_cached_result(monkeypatch) -> None:
    client = TwoGISClient()
    client.api_key = "test"  # avoid log noise
    client.redis_client = object()

    cached = (56.3, 44.0)
    cached_list: List[float] = list(cached)

    get_cached = AsyncMock(return_value=cached_list)
    monkeypatch.setattr(client, "_get_cached", get_cached)
    geocode_places = AsyncMock()
    monkeypatch.setattr(client, "_geocode_places", geocode_places)

    result = await client.geocode("ул. Большая Покровская, 1")

    assert result == cached
    geocode_places.assert_not_called()


@pytest.mark.asyncio
async def test_twogis_client_falls_back_to_address_lookup(monkeypatch) -> None:
    client = TwoGISClient()
    client.api_key = "test"
    client.redis_client = object()

    monkeypatch.setattr(client, "_get_cached", AsyncMock(return_value=None))
    monkeypatch.setattr(client, "_geocode_places", AsyncMock(return_value=None))
    monkeypatch.setattr(client, "_set_cache", AsyncMock())

    fallback_coords = (56.31, 44.01)
    monkeypatch.setattr(client, "_geocode_address", AsyncMock(return_value=fallback_coords))

    result = await client.geocode("Площадь Минина")

    assert result == fallback_coords
    client._set_cache.assert_awaited()


def test_twogis_client_cache_key_is_stable() -> None:
    client = TwoGISClient()
    params = {"q": "test", "page": 1}

    assert client._cache_key("geocode", params) == client._cache_key("geocode", {"page": 1, "q": "test"})


def test_twogis_client_parse_distance_matrix() -> None:
    client = TwoGISClient()
    matrix_data = {
        "routes": [
            {"source_index": 0, "target_index": 0, "distance": 1200},
            {"source_index": 0, "target_index": 1, "distance": 3400},
            {"source_index": 1, "target_index": 0, "distance": 800},
        ]
    }

    matrix = client.parse_distance_matrix(matrix_data, num_sources=2, num_targets=2)

    assert matrix == [[1.2, 3.4], [0.8, math.inf]]


def test_twogis_client_parse_geometry_from_wkt() -> None:
    client = TwoGISClient()
    route_data = {
        "maneuvers": [
            {
                "outcoming_path": {
                    "geometry": [
                        {"selection": "LINESTRING(44.0000 56.3200, 44.0100 56.3300)"},
                        {"selection": "LINESTRING(44.0100 56.3300, 44.0150 56.3350)"},
                    ]
                }
            }
        ]
    }

    points = client.parse_geometry(route_data)

    assert points == [(56.32, 44.0), (56.33, 44.01), (56.335, 44.015)]


def test_twogis_client_parse_geometry_fallback_to_waypoints() -> None:
    client = TwoGISClient()
    route_data = {
        "waypoints": [
            {"projected_point": {"lat": 56.31, "lon": 44.01}},
            {"original_point": {"lat": 56.33, "lon": 44.02}},
        ]
    }

    points = client.parse_geometry(route_data)

    assert points == [(56.31, 44.01), (56.33, 44.02)]


def test_twogis_client_parse_wkt_handles_invalid_input(caplog) -> None:
    client = TwoGISClient()
    with caplog.at_level("ERROR"):
        points = client._parse_wkt_linestring("INVALID")

    assert points == []


def test_twogis_client_calculate_distance() -> None:
    client = TwoGISClient()
    distance = client.calculate_distance(56.3269, 44.0073, 56.3287, 44.002)

    assert 0.2 < distance < 0.5
