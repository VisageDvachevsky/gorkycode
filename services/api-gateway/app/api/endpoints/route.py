from __future__ import annotations

import logging
from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException

from app.grpc.clients import grpc_clients
from app.models.schemas import (
    CoffeePreferences,
    POIInRoute,
    RouteRequest,
    RouteResponse,
)
from app.proto import llm_pb2, route_pb2

logger = logging.getLogger(__name__)

router = APIRouter()

WALK_SPEED_KMH = 4.5
DEFAULT_VISIT_MINUTES = 45


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points."""
    radius = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    a = (
        sin(d_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(d_lon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius * c


def _minutes_from_distance(distance_km: float) -> float:
    if distance_km <= 0:
        return 0.0
    return (distance_km / WALK_SPEED_KMH) * 60.0


def _map_intensity_for_ranking(intensity: str) -> str:
    mapping = {
        "relaxed": "low",
        "low": "low",
        "intense": "high",
        "high": "high",
    }
    return mapping.get(intensity, "medium")


def _map_intensity_for_llm(intensity: str) -> str:
    mapping = {
        "low": "relaxed",
        "relaxed": "relaxed",
        "high": "intense",
        "intense": "intense",
    }
    return mapping.get(intensity, intensity)


def _build_profile_text(request: RouteRequest) -> str:
    parts: List[str] = []

    if request.interests:
        parts.append(f"Интересы: {request.interests}")

    if request.categories:
        parts.append("Категории: " + ", ".join(request.categories))

    parts.append(f"Формат прогулки: {request.social_mode}")
    parts.append(f"Интенсивность: {request.intensity}")
    parts.append(f"Длительность: {request.hours:.1f} часа")

    return ". ".join(parts)


def _fallback_summary(poi_names: List[str]) -> str:
    if not poi_names:
        return "Не удалось сформировать описание маршрута."
    joined = ", ".join(poi_names)
    return f"Предлагаем прогулку по Нижнему Новгороду через точки: {joined}."


def _fallback_why(name: str, description: Optional[str]) -> str:
    base = description.strip() if description else "Уникальная точка маршрута."
    return f"{name}: {base}"


def _stable_coffee_id(source_id: str) -> int:
    return abs(hash(source_id)) % 900_000 + 100_000


async def _resolve_start_location(request: RouteRequest) -> Tuple[float, float, str]:
    lat: Optional[float] = request.start_lat
    lon: Optional[float] = request.start_lon
    label = request.start_address or "Заданная точка старта"

    if lat is None or lon is None:
        if not request.start_address:
            raise HTTPException(
                status_code=400,
                detail="Необходимо указать адрес или координаты старта",
            )
        try:
            geocode = await grpc_clients.geocoding_client.geocode_address(
                request.start_address
            )
        except Exception as exc:
            logger.exception("Geocoding request failed")
            raise HTTPException(503, "Сервис геокодинга недоступен") from exc

        if not geocode.success:
            raise HTTPException(400, "Не удалось распознать адрес старта")

        lat = geocode.lat
        lon = geocode.lon
        label = geocode.formatted_address or request.start_address

    try:
        validation = await grpc_clients.geocoding_client.validate_coordinates(lat, lon)
    except Exception as exc:
        logger.exception("Coordinate validation failed")
        raise HTTPException(503, "Сервис геокодинга недоступен") from exc

    if not validation.valid:
        raise HTTPException(400, validation.reason or "Старт вне доступной зоны")

    return float(lat), float(lon), label


async def _maybe_add_coffee_break(
    preferences: CoffeePreferences,
    current_lat: float,
    current_lon: float,
    cursor_time: datetime,
    order_number: int,
) -> Optional[Tuple[POIInRoute, datetime, float, float, float]]:
    radius = preferences.search_radius_km or 0.6

    try:
        cafes = await grpc_clients.poi_client.find_cafes_near_location(
            lat=current_lat,
            lon=current_lon,
            radius_km=radius,
        )
    except Exception as exc:
        logger.warning("Failed to query cafes: %s", exc)
        return None

    if not cafes:
        return None

    cafe = min(cafes, key=lambda c: c.distance if c.distance else 0.0)
    walk_km = _haversine_km(current_lat, current_lon, cafe.lat, cafe.lon)
    walk_minutes = _minutes_from_distance(walk_km)
    arrival_time = cursor_time + timedelta(minutes=walk_minutes)

    stay_minutes = max(15, min(30, preferences.interval_minutes // 3))
    leave_time = arrival_time + timedelta(minutes=stay_minutes)

    why = (
        f"Сделайте паузу в {cafe.name}: уютное место неподалёку для кофе и отдыха."
    )
    tip_parts = ["Закажите напиток на вынос, чтобы продолжить прогулку без спешки."]
    if cafe.address:
        tip_parts.append(f"Адрес: {cafe.address}.")
    tip = " ".join(tip_parts)

    coffee_item = POIInRoute(
        order=order_number,
        poi_id=_stable_coffee_id(cafe.id or cafe.name),
        name=cafe.name,
        lat=cafe.lat,
        lon=cafe.lon,
        why=why,
        tip=tip,
        est_visit_minutes=stay_minutes,
        arrival_time=arrival_time,
        leave_time=leave_time,
        is_coffee_break=True,
    )

    return coffee_item, leave_time, cafe.lat, cafe.lon, walk_km


@router.post("/plan", response_model=RouteResponse)
async def plan_route(request: RouteRequest) -> RouteResponse:
    """Plan personalized tourist route via gRPC microservices."""

    start_lat, start_lon, start_label = await _resolve_start_location(request)
    tz = request.resolved_timezone()

    start_time = None
    if request.start_time:
        start_time = datetime.strptime(request.start_time, "%H:%M")
        now = datetime.now(tz)
        start_time = start_time.replace(year=now.year, month=now.month, day=now.day)
        start_time = start_time.replace(tzinfo=tz)
    else:
        start_time = datetime.now(tz)

    profile_text = _build_profile_text(request)

    try:
        embedding_response = await grpc_clients.embedding_client.generate_embedding(
            text=profile_text or "Прогулка по Нижнему Новгороду",
            use_cache=True,
        )
    except Exception as exc:
        logger.exception("Embedding service error")
        raise HTTPException(503, "Сервис эмбеддингов недоступен") from exc

    user_embedding = list(embedding_response.vector)
    if not user_embedding:
        raise HTTPException(503, "Не удалось построить профиль пользователя")

    try:
        ranking_response = await grpc_clients.ranking_client.rank_pois(
            user_embedding=user_embedding,
            social_mode=request.social_mode,
            intensity=_map_intensity_for_ranking(request.intensity),
            top_k=25,
            categories_filter=request.categories or [],
        )
    except Exception as exc:
        logger.exception("Ranking service error")
        raise HTTPException(503, "Сервис ранжирования недоступен") from exc

    scored_pois = list(ranking_response)
    if not scored_pois:
        raise HTTPException(404, "Под ваши предпочтения не нашли подходящих мест")

    candidates = [
        route_pb2.POIInfo(
            id=poi.poi_id,
            name=poi.name,
            lat=poi.lat,
            lon=poi.lon,
            avg_visit_minutes=poi.avg_visit_minutes or DEFAULT_VISIT_MINUTES,
            rating=poi.rating or 0.0,
        )
        for poi in scored_pois[:15]
    ]

    try:
        route_plan = await grpc_clients.route_planner_client.optimize_route(
            start_lat=start_lat,
            start_lon=start_lon,
            pois=candidates,
            available_hours=request.hours,
        )
    except Exception as exc:
        logger.exception("Route planner error")
        raise HTTPException(503, "Сервис построения маршрутов недоступен") from exc

    if not route_plan.optimized_route:
        raise HTTPException(404, "Не удалось построить маршрут в заданное время")

    ordered_infos: List[route_pb2.POIInfo] = list(route_plan.optimized_route)
    ranked_by_id = {poi.poi_id: poi for poi in scored_pois}

    # Optionally enrich with metadata from POI service
    full_details: Dict[int, Dict] = {}
    needed_categories = {
        ranked_by_id[info.id].category
        for info in ordered_infos
        if info.id in ranked_by_id and ranked_by_id[info.id].category
    }
    try:
        if needed_categories:
            poi_details = await grpc_clients.poi_client.get_all_pois(
                categories=list(needed_categories),
                with_embeddings=False,
            )
            full_details = {poi.id: poi for poi in poi_details}
    except Exception as exc:
        logger.warning("Failed to fetch POI metadata: %s", exc)

    ordered: List[Dict] = []
    for poi_info in ordered_infos:
        poi_id = poi_info.id
        ranked = ranked_by_id.get(poi_id)
        if not ranked:
            continue
        details = full_details.get(poi_id)
        ordered.append(
            {
                "id": poi_id,
                "name": poi_info.name,
                "lat": poi_info.lat,
                "lon": poi_info.lon,
                "avg_visit_minutes": poi_info.avg_visit_minutes or DEFAULT_VISIT_MINUTES,
                "rating": ranked.rating or 0.0,
                "category": ranked.category,
                "description": ranked.description,
                "tags": list(ranked.tags),
                "local_tip": getattr(details, "local_tip", None),
                "address": getattr(details, "address", ""),
            }
        )

    if not ordered:
        raise HTTPException(404, "Не удалось собрать информацию по точкам маршрута")

    llm_request = llm_pb2.RouteExplanationRequest(
        route=[
            llm_pb2.POIContext(
                id=item["id"],
                name=item["name"],
                description=item["description"] or "",
                category=item["category"],
                tags=item["tags"],
                local_tip=item.get("local_tip", "") or "",
            )
            for item in ordered
        ],
        user_interests=request.interests or ", ".join(request.categories or []),
        social_mode=request.social_mode,
        intensity=_map_intensity_for_llm(request.intensity),
    )

    llm_response = None
    try:
        llm_response = await grpc_clients.llm_client.generate_route_explanation(llm_request)
    except Exception as exc:
        logger.warning("LLM service unavailable, falling back to static texts: %s", exc)

    explanation_map = {}
    summary = _fallback_summary([item["name"] for item in ordered])
    atmosphere = None
    notes_from_llm: List[str] = []

    if llm_response:
        summary = llm_response.summary or summary
        atmosphere = llm_response.atmospheric_description or None
        notes_from_llm = list(llm_response.notes)
        explanation_map = {exp.poi_id: exp for exp in llm_response.explanations}

    cursor_time = start_time
    total_distance_km = 0.0
    route_items: List[POIInRoute] = []
    initial_time = start_time
    current_lat, current_lon = start_lat, start_lon
    order_counter = 1
    coffee_added = False

    for item in ordered:
        walk_km = _haversine_km(current_lat, current_lon, item["lat"], item["lon"])
        walk_minutes = _minutes_from_distance(walk_km)
        if walk_minutes:
            cursor_time += timedelta(minutes=walk_minutes)
            total_distance_km += walk_km

        explanation = explanation_map.get(item["id"])
        visit_minutes = item["avg_visit_minutes"] or DEFAULT_VISIT_MINUTES
        leave_time = cursor_time + timedelta(minutes=visit_minutes)

        route_items.append(
            POIInRoute(
                order=order_counter,
                poi_id=item["id"],
                name=item["name"],
                lat=item["lat"],
                lon=item["lon"],
                why=(explanation.why if explanation and explanation.why else _fallback_why(item["name"], item["description"])),
                tip=(explanation.tip if explanation and explanation.tip else (item.get("local_tip") or "")),
                est_visit_minutes=int(visit_minutes),
                arrival_time=cursor_time,
                leave_time=leave_time,
                is_coffee_break=False,
            )
        )

        cursor_time = leave_time
        current_lat, current_lon = item["lat"], item["lon"]
        order_counter += 1

        if (
            request.coffee_preferences
            and request.coffee_preferences.enabled
            and not coffee_added
            and (cursor_time - initial_time).total_seconds() / 60.0 >= request.coffee_preferences.interval_minutes
        ):
            coffee_data = await _maybe_add_coffee_break(
                preferences=request.coffee_preferences,
                current_lat=current_lat,
                current_lon=current_lon,
                cursor_time=cursor_time,
                order_number=order_counter,
            )
            if coffee_data:
                coffee_item, new_cursor_time, coffee_lat, coffee_lon, walk_km_to_cafe = coffee_data
                total_distance_km += walk_km_to_cafe
                route_items.append(coffee_item)
                cursor_time = new_cursor_time
                current_lat, current_lon = coffee_lat, coffee_lon
                order_counter += 1
                coffee_added = True

    total_est_minutes = int(round((cursor_time - initial_time).total_seconds() / 60.0))
    route_geometry = [[start_lat, start_lon]] + [[item.lat, item.lon] for item in route_items]

    notes: List[str] = [f"Старт: {start_label}"]
    if coffee_added:
        notes.append("Запланирована кофейная пауза по вашим предпочтениям")
    notes.extend(notes_from_llm)

    time_limit_minutes = int(request.hours * 60)
    warnings: List[str] = []
    if total_est_minutes > time_limit_minutes:
        warnings.append(
            "Маршрут получился чуть длиннее указанного времени — скорректируйте длительность или интересы."
        )

    response = RouteResponse(
        summary=summary,
        route=route_items,
        total_est_minutes=total_est_minutes,
        total_distance_km=round(total_distance_km, 2),
        notes=notes,
        atmospheric_description=atmosphere,
        route_geometry=route_geometry,
        start_time_used=initial_time,
        time_warnings=warnings,
    )

    return response
