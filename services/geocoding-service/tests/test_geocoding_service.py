from unittest.mock import AsyncMock

import grpc
import pytest

import sys
from pathlib import Path
import types


SERVICE_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = SERVICE_ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

if "app" in sys.modules:
    app_module = sys.modules["app"]
    module_file = getattr(app_module, "__file__", "")
    if module_file and "backend/app" in Path(module_file).as_posix():
        sys.modules.pop("app", None)
        sys.modules.pop("app.services", None)
        sys.modules.pop("app.services.geocoding", None)
        sys.modules.pop("app.proto", None)

if "app" not in sys.modules:
    package = types.ModuleType("app")
    package.__path__ = [str(APP_DIR)]
    sys.modules["app"] = package

from app.proto import geocoding_pb2
from app.services import geocoding as geocoding_module
from app.services.geocoding import GeocodingService, GeocodingServicer


@pytest.fixture
def service() -> GeocodingService:
    return GeocodingService()


@pytest.mark.asyncio
async def test_geocode_address_returns_coordinates(monkeypatch, service: GeocodingService) -> None:
    expected = (56.25, 43.95)
    monkeypatch.setattr(geocoding_module.twogis_client, "geocode", AsyncMock(return_value=expected))

    coords = await service.geocode_address("ул. Большая Покровская")

    assert coords == expected


@pytest.mark.asyncio
async def test_geocode_address_rejects_out_of_bounds(monkeypatch, service: GeocodingService) -> None:
    monkeypatch.setattr(
        geocoding_module.twogis_client, "geocode", AsyncMock(return_value=(55.75, 37.61))
    )

    coords = await service.geocode_address("Москва")

    assert coords is None


@pytest.mark.asyncio
async def test_reverse_geocode_validates_coordinates(monkeypatch, service: GeocodingService) -> None:
    monkeypatch.setattr(geocoding_module.twogis_client, "reverse_geocode", AsyncMock(return_value="Адрес"))

    assert await service.reverse_geocode(56.32, 44.0) == "Адрес"
    assert await service.reverse_geocode(0.0, 0.0) is None


class FakeContext:
    def __init__(self) -> None:
        self.code = None
        self.details = None

    def set_code(self, code) -> None:  # pragma: no cover - trivial
        self.code = code

    def set_details(self, details: str) -> None:  # pragma: no cover - trivial
        self.details = details


@pytest.mark.asyncio
async def test_servicer_geocode_success(monkeypatch) -> None:
    service = GeocodingService()
    servicer = GeocodingServicer(service=service)

    coords = (56.25, 43.95)
    monkeypatch.setattr(service, "geocode_address", AsyncMock(return_value=coords))
    monkeypatch.setattr(service, "reverse_geocode", AsyncMock(return_value="Formatted"))

    response = await servicer.GeocodeAddress(
        geocoding_pb2.GeocodeRequest(address="Кремль", city="Нижний Новгород"),
        FakeContext(),
    )

    assert response.success
    assert response.lat == coords[0]
    assert response.lon == coords[1]
    assert response.formatted_address == "Formatted"


@pytest.mark.asyncio
async def test_servicer_geocode_handles_failure(monkeypatch) -> None:
    service = GeocodingService()
    servicer = GeocodingServicer(service=service)
    context = FakeContext()

    async def raise_error(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "geocode_address", AsyncMock(side_effect=raise_error))

    response = await servicer.GeocodeAddress(
        geocoding_pb2.GeocodeRequest(address=""),
        context,
    )

    assert not response.success
    assert context.code == grpc.StatusCode.INTERNAL
    assert "boom" in context.details


@pytest.mark.asyncio
async def test_servicer_validate_coordinates(monkeypatch) -> None:
    service = GeocodingService()
    servicer = GeocodingServicer(service=service)

    response_valid = await servicer.ValidateCoordinates(
        geocoding_pb2.CoordinateValidationRequest(lat=56.3, lon=44.0),
        FakeContext(),
    )
    response_invalid = await servicer.ValidateCoordinates(
        geocoding_pb2.CoordinateValidationRequest(lat=0, lon=0),
        FakeContext(),
    )

    assert response_valid.valid
    assert not response_invalid.valid


@pytest.mark.asyncio
async def test_servicer_initialize_connects_redis(monkeypatch) -> None:
    monkeypatch.setattr(geocoding_module.twogis_client, "connect_redis", AsyncMock())

    servicer = GeocodingServicer()
    await servicer.initialize()

    geocoding_module.twogis_client.connect_redis.assert_awaited_once()
