from __future__ import annotations

import logging

import httpx

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.models.schemas import RouteRequest, RouteResponse
from app.services.share_store import share_store

from app.domain.route_planning.exceptions import RoutePlanningError
from app.domain.route_planning.metadata import build_metadata, is_history, is_street_art
from app.domain.route_planning.scoring import apply_time_window_filters
from app.domain.route_planning.service import RoutePlanner

logger = logging.getLogger(__name__)

router = APIRouter()


def _apply_time_window_filters(pois, *, start_hour: int | None = None):
    return apply_time_window_filters(pois, start_time=None, start_hour=start_hour)


def _alternate_street_history_candidates(pois):
    typed = [(poi, build_metadata(poi)) for poi in pois]
    history = [poi for poi, meta in typed if is_history(meta)]
    street = [poi for poi, meta in typed if is_street_art(meta)]
    if not history or not street:
        return list(pois)

    alternated: list = []
    idx_history = idx_street = 0
    use_history = True
    while idx_history < len(history) or idx_street < len(street):
        if use_history and idx_history < len(history):
            alternated.append(history[idx_history])
            idx_history += 1
        elif not use_history and idx_street < len(street):
            alternated.append(street[idx_street])
            idx_street += 1
        elif idx_history < len(history):
            alternated.append(history[idx_history])
            idx_history += 1
        elif idx_street < len(street):
            alternated.append(street[idx_street])
            idx_street += 1
        use_history = not use_history

    remaining = [poi for poi, _ in typed if poi not in alternated]
    alternated.extend(remaining)
    return alternated


def _is_history_candidate(poi) -> bool:
    return is_history(build_metadata(poi))


def _is_street_art_candidate(poi) -> bool:
    return is_street_art(build_metadata(poi))


async def _fetch_weather_advice(
    lat: float,
    lon: float,
    highlight_name: str | None,
    intensity: str | None,
) -> str:
    params = {"format": "j1", "lat": lat, "lon": lon}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://wttr.in", params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return "Погоду уточнить не удалось — возьмите зонт на всякий случай"

    condition_payload = (
        (payload.get("current_condition") or [{}])[0] if isinstance(payload, dict) else {}
    )
    raw_description = (
        ((condition_payload.get("weatherDesc") or [{}])[0]).get("value")
        if isinstance(condition_payload, dict)
        else None
    )
    description = (raw_description or "").lower()
    if "rain" in description or "дожд" in description:
        description = "дождливо"
    elif not description:
        description = "переменная облачность"

    temp_c = condition_payload.get("temp_C")
    precip_mm = condition_payload.get("precipMM")
    parts = [description]
    if temp_c not in (None, ""):
        parts.append(f"{temp_c}°C")
    if precip_mm not in (None, ""):
        parts.append(f"осадки {precip_mm} мм")

    summary = ", ".join(parts)
    highlight = (highlight_name or "место").lower()
    intensity_note = "" if not intensity else f" (формат {intensity})"
    return (
        f"Сегодня {summary}{intensity_note}, {highlight} всё равно порадует, "
        "подходящая одежда обязательна"
    )


@router.post("/plan", response_model=RouteResponse)
async def plan_route(request: RouteRequest) -> RouteResponse:
    planner = RoutePlanner(request)
    try:
        response = await planner.plan()
    except RoutePlanningError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    await share_store.save_route(
        response.share_token,
        response.model_dump(mode="json", exclude_none=True),
    )
    return response


@router.get("/share/{token}", response_model=RouteResponse)
async def load_shared_route(token: str) -> RouteResponse:
    data = await share_store.load_route(token)
    if not data:
        raise HTTPException(404, "Ссылка недействительна или срок хранения истёк")

    try:
        route = RouteResponse.model_validate(data)
    except ValidationError as exc:
        logger.warning("Stored route for %s failed validation: %s", token, exc)
        raise HTTPException(500, "Не удалось восстановить маршрут") from exc

    await share_store.extend_ttl(token)
    return route
