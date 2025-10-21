from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

fake_common = ModuleType("ai_tourist_common")
fake_common.get_trace_id = lambda: "-"
sys.modules.setdefault("ai_tourist_common", fake_common)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api.endpoints import route


def make_poi(name: str, *, tags: list[str] | None = None, category: str | None = None, rating: float | None = None):
    return SimpleNamespace(name=name, tags=tags or [], category=category, rating=rating)


def test_apply_time_window_filters_excludes_morning_cafes():
    pois = [
        make_poi("Кофейня Смена", tags=["кофе"]),
        make_poi("Музей истории", tags=["музей"]),
    ]

    filtered = route._apply_time_window_filters(pois, start_hour=8)

    names = {poi.name for poi in filtered}
    assert "Кофейня Смена" not in names
    assert "Музей истории" in names


def test_apply_time_window_filters_prioritises_preferred_night_spots():
    pois = [
        make_poi("Тёмный двор", tags=["двор"], rating=4.7),
        make_poi("Набережная", tags=["набережная"], rating=4.9),
        make_poi("Центральная площадь", tags=["центр"], rating=4.6),
    ]

    filtered = route._apply_time_window_filters(pois, start_hour=22)

    names = [poi.name for poi in filtered]
    assert "Тёмный двор" not in names
    assert names[0] == "Набережная"


def test_alternate_street_history_candidates_interleaves_types():
    pois = [
        make_poi("Панорама истории", category="museum"),
        make_poi("Уличный мурал", category="art_object"),
        make_poi("Музей памяти", category="monument"),
        make_poi("Граффити двор", tags=["стрит-арт"]),
        make_poi("Кофейный угол", tags=["кофе"]),
    ]

    alternated = route._alternate_street_history_candidates(pois)

    sequence = []
    for poi in alternated[:4]:
        if route._is_history_candidate(poi):
            sequence.append("history")
        elif route._is_street_art_candidate(poi):
            sequence.append("street")
    assert sequence[:4] == ["history", "street", "history", "street"]
    assert alternated[-1].name == "Кофейный угол"


@pytest.mark.asyncio
async def test_fetch_weather_advice_builds_descriptive_message(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "current_condition": [
                    {
                        "weatherDesc": [{"value": "Light rain"}],
                        "temp_C": "7",
                        "precipMM": "2.5",
                        "windspeedKmph": "12",
                    }
                ]
            }

    class DummyClient:
        async def __aenter__(self) -> "DummyClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def get(self, url: str, params: dict | None = None) -> DummyResponse:
            captured["request"] = (url, params)
            return DummyResponse()

    def fake_async_client(*args, **kwargs):
        return DummyClient()

    monkeypatch.setattr(route.httpx, "AsyncClient", fake_async_client)

    advice = await route._fetch_weather_advice(56.3, 44.0, "Кремль")

    assert "дождливо" in advice.lower()
    assert "кремль" in advice.lower()
    assert captured["request"][0].startswith("https://wttr.in")
