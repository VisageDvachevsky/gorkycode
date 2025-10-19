import pytest

from app.services.routing import RoutingService
from app.services.transit import TransitService, transit_service


@pytest.fixture
def transit_service_instance():
    service = TransitService()
    service.api_key = "test-key"
    service.redis_client = None
    return service


def _sample_navitia_response():
    return {
        "journeys": [
            {
                "duration": 1800,
                "sections": [
                    {
                        "type": "street_network",
                        "mode": "walking",
                        "duration": 600,
                        "length": 750,
                        "geojson": {
                            "type": "LineString",
                            "coordinates": [
                                [43.9000, 56.3000],
                                [43.9010, 56.3010],
                            ],
                        },
                    },
                    {
                        "type": "public_transport",
                        "duration": 900,
                        "departure_date_time": "20240101T101500",
                        "arrival_date_time": "20240101T103000",
                        "display_informations": {
                            "code": "25",
                            "direction": "Площадь Свободы",
                            "commercial_mode": "автобус",
                            "physical_mode": "Bus",
                        },
                        "from": {
                            "name": "Улица Ленина",
                            "coord": {"lat": 56.3012, "lon": 43.9012},
                            "stop_point": {
                                "platform": {"name": "1"},
                            },
                        },
                        "to": {
                            "name": "Площадь Свободы",
                            "coord": {"lat": 56.3200, "lon": 43.9300},
                        },
                    },
                ],
            }
        ]
    }


def test_parse_navitia_response_enriched(transit_service_instance):
    result = transit_service_instance._parse_navitia_response(_sample_navitia_response())

    assert result is not None
    assert result["summary"].startswith("Автобус")
    assert result["total_duration_min"] == 30
    assert result["total_walking_min"] == 10
    assert any("сторона" in instr for instr in result["instructions"])
    assert result["transit_lines"][0]["platform"] == "1"


@pytest.mark.asyncio
async def test_routing_service_transit_suggestion(monkeypatch):
    service = RoutingService()

    monkeypatch.setattr(service, "calculate_distance_km", lambda *args, **kwargs: 3.5)
    monkeypatch.setattr(service, "_estimate_walking_time", lambda distance: 45)

    async def fake_get_transit_route(*args, **kwargs):
        return {
            "summary": "Автобус 25 до Площадь Свободы",
            "total_duration_min": 20,
            "instructions": ["Сядьте на остановке", "Выйдите на остановке"],
            "total_walking_min": 8,
            "transit_lines": [
                {
                    "line": "25",
                    "from_stop": "Улица Ленина",
                    "to_stop": "Площадь Свободы",
                    "duration_min": 15,
                }
            ],
        }

    monkeypatch.setattr(transit_service, "should_suggest_transit", lambda distance: True)
    monkeypatch.setattr(transit_service, "get_transit_route", fake_get_transit_route)

    suggestion = await service.get_transit_suggestion((56.3, 43.9), (56.32, 43.92))

    assert suggestion is not None
    assert suggestion["time_saved_min"] == 25
    assert suggestion["instructions"]
    assert suggestion["transit_lines"][0]["line"] == "25"
