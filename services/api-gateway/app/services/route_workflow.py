from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from math import atan2, cos, radians, sin, sqrt
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from fastapi import HTTPException

from app.grpc.clients import GRPCClients, grpc_clients
from app.models.schemas import (
    CoffeePreferences,
    CoordinatePoint,
    ManeuverInstruction,
    POIInRoute,
    RouteLegInstruction,
    RouteRequest,
    RouteResponse,
    TransitGuidance,
    TransitStopInfo,
)
from app.proto import llm_pb2, route_pb2

logger = logging.getLogger(__name__)

WALK_SPEED_KMH = 4.5
DEFAULT_VISIT_MINUTES = 45

INTENSITY_PROFILES: Dict[str, Dict[str, float]] = {
    "relaxed": {
        "walk_speed_multiplier": 0.85,
        "visit_duration_multiplier": 1.3,
        "min_visit_minutes": 25,
        "max_visit_minutes": 75,
    },
    "medium": {
        "walk_speed_multiplier": 1.0,
        "visit_duration_multiplier": 1.0,
        "min_visit_minutes": 20,
        "max_visit_minutes": 60,
    },
    "intense": {
        "walk_speed_multiplier": 1.15,
        "visit_duration_multiplier": 0.75,
        "min_visit_minutes": 15,
        "max_visit_minutes": 45,
    },
}


@dataclass(frozen=True)
class StartContext:
    lat: float
    lon: float
    label: str
    timezone: tzinfo
    start_time: datetime


@dataclass
class CandidateBundle:
    planner_inputs: List[route_pb2.POIInfo]
    ranked_by_id: Dict[int, Any]
    details_prefetch: Optional[asyncio.Task[List[Any]]]


@dataclass
class LLMResult:
    summary: str
    atmosphere: Optional[str]
    notes: List[str]
    explanations: Dict[int, llm_pb2.POIExplanation]


@dataclass
class ItineraryResult:
    items: List[POIInRoute]
    total_distance_km: float
    walking_distance_km: float
    transit_distance_km: float
    total_minutes: int
    geometry_points: List[Tuple[float, float]]
    base_notes: List[str]


class RoutePlanningWorkflow:
    """High-level orchestration of the route planning pipeline."""

    def __init__(self, clients: GRPCClients = grpc_clients) -> None:
        self.clients = clients

    async def plan(self, request: RouteRequest) -> RouteResponse:
        """Build a personalised route for the incoming request."""

        details_task: Optional[asyncio.Task[List[Any]]] = None

        try:
            start_ctx = await self._prepare_start_context(request)

            user_embedding = await self._generate_embedding(_build_profile_text(request))
            bundle = await self._rank_candidates(request, user_embedding)
            details_task = bundle.details_prefetch

            route_plan = await self._optimise_route(start_ctx, request, bundle.planner_inputs)

            movement_leg_msgs = list(route_plan.legs)
            movement_legs: List[RouteLegInstruction] = [
                _convert_leg_proto(leg_msg) for leg_msg in movement_leg_msgs
            ]

            ordered_infos = list(route_plan.optimized_route)
            details_by_id = await self._collect_poi_details(bundle, ordered_infos)
            details_task = None

            ordered_metadata = self._build_ordered_metadata(
                ordered_infos, bundle.ranked_by_id, details_by_id, request
            )

            llm_result = await self._fetch_llm_result(ordered_metadata, request)

            itinerary = await self._assemble_itinerary(
                request=request,
                start_ctx=start_ctx,
                ordered=ordered_metadata,
                movement_legs=movement_legs,
                llm_result=llm_result,
                route_plan=route_plan,
            )

            geometry_task = self._spawn_geometry_task(start_ctx, itinerary.geometry_points)
            route_geometry = await self._resolve_geometry(
                geometry_task, start_ctx, itinerary.geometry_points
            )

            notes = itinerary.base_notes + llm_result.notes
            warnings = self._compute_time_warnings(request, itinerary.total_minutes)

            response = RouteResponse(
                summary=llm_result.summary,
                route=itinerary.items,
                total_est_minutes=itinerary.total_minutes,
                total_distance_km=round(itinerary.total_distance_km, 2),
                notes=notes,
                atmospheric_description=llm_result.atmosphere,
                route_geometry=route_geometry,
                start_time_used=start_ctx.start_time,
                time_warnings=warnings,
                movement_legs=movement_legs,
                walking_distance_km=round(itinerary.walking_distance_km, 2),
                transit_distance_km=round(itinerary.transit_distance_km, 2),
            )

            return response

        finally:
            await self._safe_cancel(details_task)

    async def _prepare_start_context(self, request: RouteRequest) -> StartContext:
        lat, lon, label = await self._resolve_start_location(request)
        tz = request.resolved_timezone()
        start_time = self._resolve_start_time(request, tz)
        return StartContext(lat=lat, lon=lon, label=label, timezone=tz, start_time=start_time)

    async def _resolve_start_location(
        self, request: RouteRequest
    ) -> Tuple[float, float, str]:
        lat: Optional[float] = request.start_lat
        lon: Optional[float] = request.start_lon
        label = request.start_address or "Заданная точка старта"

        if lat is None or lon is None:
            if not request.start_address:
                raise HTTPException(
                    status_code=400, detail="Необходимо указать адрес или координаты старта"
                )
            try:
                geocode = await self.clients.geocoding_client.geocode_address(
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
            validation = await self.clients.geocoding_client.validate_coordinates(lat, lon)
        except Exception as exc:
            logger.exception("Coordinate validation failed")
            raise HTTPException(503, "Сервис геокодинга недоступен") from exc

        if not validation.valid:
            raise HTTPException(400, validation.reason or "Старт вне доступной зоны")

        return float(lat), float(lon), label

    def _resolve_start_time(self, request: RouteRequest, tz: tzinfo) -> datetime:
        if request.start_time:
            parsed = datetime.strptime(request.start_time, "%H:%M")
            now = datetime.now(tz)
            parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
            return parsed.replace(tzinfo=tz)
        return datetime.now(tz)

    async def _generate_embedding(self, profile_text: str) -> List[float]:
        text = profile_text or "Прогулка по Нижнему Новгороду"
        try:
            response = await self.clients.embedding_client.generate_embedding(
                text=text, use_cache=True
            )
        except Exception as exc:
            logger.exception("Embedding service error")
            raise HTTPException(503, "Сервис эмбеддингов недоступен") from exc

        vector = list(response.vector)
        if not vector:
            raise HTTPException(503, "Не удалось построить профиль пользователя")
        return vector

    async def _rank_candidates(
        self, request: RouteRequest, user_embedding: List[float]
    ) -> CandidateBundle:
        try:
            ranking_response = await self.clients.ranking_client.rank_pois(
                user_embedding=user_embedding,
                social_mode=request.social_mode,
                intensity=_map_intensity_for_ranking(request.intensity),
                top_k=25,
                categories_filter=request.categories or [],
            )
        except Exception as exc:
            logger.exception("Ranking service error")
            raise HTTPException(503, "Сервис ранжирования недоступен") from exc

        scored = list(ranking_response)
        if not scored:
            raise HTTPException(404, "Под ваши предпочтения не нашли подходящих мест")

        return self._build_candidate_bundle(scored)

    def _build_candidate_bundle(self, scored: Sequence[Any]) -> CandidateBundle:
        top = list(scored[:15])
        planner_inputs = [
            route_pb2.POIInfo(
                id=poi.poi_id,
                name=poi.name,
                lat=poi.lat,
                lon=poi.lon,
                avg_visit_minutes=poi.avg_visit_minutes or DEFAULT_VISIT_MINUTES,
                rating=poi.rating or 0.0,
            )
            for poi in top
        ]

        ranked_by_id = {poi.poi_id: poi for poi in scored}
        candidate_categories = {
            poi.category
            for poi in top
            if getattr(poi, "category", None)
        }

        details_task: Optional[asyncio.Task[List[Any]]] = None
        if candidate_categories:
            details_task = asyncio.create_task(
                self.clients.poi_client.get_all_pois(
                    categories=list(candidate_categories),
                    with_embeddings=False,
                )
            )

        return CandidateBundle(
            planner_inputs=planner_inputs,
            ranked_by_id=ranked_by_id,
            details_prefetch=details_task,
        )

    async def _optimise_route(
        self,
        start_ctx: StartContext,
        request: RouteRequest,
        candidates: Sequence[route_pb2.POIInfo],
    ) -> route_pb2.RouteOptimizationResponse:
        try:
            route_plan = await self.clients.route_planner_client.optimize_route(
                start_lat=start_ctx.lat,
                start_lon=start_ctx.lon,
                pois=list(candidates),
                available_hours=request.hours,
                intensity=request.intensity,
            )
        except Exception as exc:
            logger.exception("Route planner error")
            raise HTTPException(503, "Сервис построения маршрутов недоступен") from exc

        if not route_plan.optimized_route:
            raise HTTPException(404, "Не удалось построить маршрут в заданное время")

        return route_plan

    async def _collect_poi_details(
        self,
        bundle: CandidateBundle,
        ordered_infos: Sequence[route_pb2.POIInfo],
    ) -> Dict[int, Any]:
        details: Dict[int, Any] = {}
        task = bundle.details_prefetch
        bundle.details_prefetch = None

        if task:
            try:
                poi_details = await task
            except Exception as exc:
                logger.warning("Failed to prefetch POI metadata: %s", exc)
            else:
                details = {poi.id: poi for poi in poi_details}

        if details:
            return details

        needed_categories = {
            getattr(bundle.ranked_by_id[info.id], "category", None)
            for info in ordered_infos
            if info.id in bundle.ranked_by_id
        }
        needed_categories.discard(None)

        if not needed_categories:
            return details

        try:
            poi_details = await self.clients.poi_client.get_all_pois(
                categories=list(needed_categories),
                with_embeddings=False,
            )
        except Exception as exc:
            logger.warning("Failed to fetch POI metadata: %s", exc)
            return details

        return {poi.id: poi for poi in poi_details}

    def _build_ordered_metadata(
        self,
        ordered_infos: Sequence[route_pb2.POIInfo],
        ranked_by_id: Dict[int, Any],
        details_by_id: Dict[int, Any],
        request: RouteRequest,
    ) -> List[Dict[str, Any]]:
        ordered: List[Dict[str, Any]] = []
        for poi_info in ordered_infos:
            ranked = ranked_by_id.get(poi_info.id)
            if not ranked:
                continue

            details = details_by_id.get(poi_info.id)
            base_visit = poi_info.avg_visit_minutes or DEFAULT_VISIT_MINUTES
            effective_visit = _effective_visit_minutes(base_visit, request.intensity)
            ordered.append(
                {
                    "id": poi_info.id,
                    "name": poi_info.name,
                    "lat": poi_info.lat,
                    "lon": poi_info.lon,
                    "avg_visit_minutes": base_visit,
                    "effective_visit_minutes": effective_visit,
                    "rating": ranked.rating or 0.0,
                    "category": getattr(ranked, "category", None),
                    "description": getattr(ranked, "description", ""),
                    "tags": list(getattr(ranked, "tags", [])),
                    "local_tip": getattr(details, "local_tip", None),
                    "address": getattr(details, "address", ""),
                }
            )

        if not ordered:
            raise HTTPException(404, "Не удалось собрать информацию по точкам маршрута")

        return ordered

    async def _fetch_llm_result(
        self, ordered: Sequence[Dict[str, Any]], request: RouteRequest
    ) -> LLMResult:
        poi_names = [item["name"] for item in ordered]
        summary = _fallback_summary(poi_names)
        atmosphere: Optional[str] = None
        notes: List[str] = []
        explanations: Dict[int, llm_pb2.POIExplanation] = {}

        if not ordered:
            return LLMResult(summary=summary, atmosphere=None, notes=[], explanations={})

        llm_request = llm_pb2.RouteExplanationRequest(
            route=[
                llm_pb2.POIContext(
                    id=item["id"],
                    name=item["name"],
                    description=item.get("description") or "",
                    category=item.get("category") or "",
                    tags=item.get("tags") or [],
                    local_tip=item.get("local_tip") or "",
                )
                for item in ordered
            ],
            user_interests=request.interests or ", ".join(request.categories or []),
            social_mode=request.social_mode,
            intensity=_map_intensity_for_llm(request.intensity),
        )

        try:
            llm_response = await self.clients.llm_client.generate_route_explanation(llm_request)
        except Exception as exc:
            logger.warning("LLM service unavailable, falling back to static texts: %s", exc)
            return LLMResult(summary=summary, atmosphere=None, notes=[], explanations={})

        summary = llm_response.summary or summary
        atmosphere = llm_response.atmospheric_description or None
        notes = list(llm_response.notes)
        explanations = {exp.poi_id: exp for exp in llm_response.explanations}
        return LLMResult(summary=summary, atmosphere=atmosphere, notes=notes, explanations=explanations)

    async def _assemble_itinerary(
        self,
        request: RouteRequest,
        start_ctx: StartContext,
        ordered: Sequence[Dict[str, Any]],
        movement_legs: Sequence[RouteLegInstruction],
        llm_result: LLMResult,
        route_plan: route_pb2.RouteOptimizationResponse,
    ) -> ItineraryResult:
        cursor_time = start_ctx.start_time
        initial_time = start_ctx.start_time
        current_lat, current_lon = start_ctx.lat, start_ctx.lon
        order_counter = 1
        coffee_added = False

        total_distance_calc = 0.0
        walking_distance_calc = 0.0
        transit_distance_calc = 0.0
        extra_walking_km = 0.0

        route_items: List[POIInRoute] = []
        base_notes: List[str] = [f"Старт: {start_ctx.label}"]

        for idx, item in enumerate(ordered):
            leg_info = movement_legs[idx] if idx < len(movement_legs) else None
            if leg_info is None:
                logger.debug("No precomputed leg for segment %s, using haversine", idx)

            leg_distance = leg_info.distance_km if leg_info else None
            if leg_distance is None:
                leg_distance = _haversine_km(current_lat, current_lon, item["lat"], item["lon"])

            leg_duration = leg_info.duration_minutes if leg_info else None
            if leg_duration is None:
                leg_duration = _minutes_from_distance(leg_distance, request.intensity)

            if leg_distance is not None:
                total_distance_calc += leg_distance
                if leg_info:
                    if leg_info.mode == "transit":
                        transit_distance_calc += leg_distance
                    else:
                        walking_distance_calc += leg_distance
                else:
                    walking_distance_calc += leg_distance

            if leg_duration:
                cursor_time += timedelta(minutes=leg_duration)

            explanation = llm_result.explanations.get(item["id"])
            visit_minutes = item.get("effective_visit_minutes") or _effective_visit_minutes(
                item.get("avg_visit_minutes"), request.intensity
            )
            leave_time = cursor_time + timedelta(minutes=visit_minutes)

            why_text = (
                explanation.why
                if explanation and explanation.why
                else _fallback_why(item["name"], item.get("description"))
            )
            tip_text = explanation.tip if explanation and explanation.tip else item.get("local_tip")
            tip_text = tip_text or None

            route_items.append(
                POIInRoute(
                    order=order_counter,
                    poi_id=item["id"],
                    name=item["name"],
                    lat=item["lat"],
                    lon=item["lon"],
                    why=why_text,
                    tip=tip_text,
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
                and (cursor_time - initial_time).total_seconds() / 60.0
                >= request.coffee_preferences.interval_minutes
            ):
                coffee_data = await self._maybe_add_coffee_break(
                    preferences=request.coffee_preferences,
                    current_lat=current_lat,
                    current_lon=current_lon,
                    cursor_time=cursor_time,
                    order_number=order_counter,
                    intensity=request.intensity,
                )
                if coffee_data:
                    (
                        coffee_item,
                        new_cursor_time,
                        coffee_lat,
                        coffee_lon,
                        walk_km_to_cafe,
                    ) = coffee_data
                    total_distance_calc += walk_km_to_cafe
                    walking_distance_calc += walk_km_to_cafe
                    extra_walking_km += walk_km_to_cafe
                    route_items.append(coffee_item)
                    cursor_time = new_cursor_time
                    current_lat, current_lon = coffee_lat, coffee_lon
                    order_counter += 1
                    coffee_added = True
                    base_notes.append("Запланирована кофейная пауза по вашим предпочтениям")

        planned_total = route_plan.total_distance_km or 0.0
        total_distance_km = max(planned_total, total_distance_calc)

        base_walking = route_plan.total_walking_distance_km or 0.0
        walking_distance_km = (
            base_walking if base_walking > 0 else walking_distance_calc
        ) + extra_walking_km

        base_transit = route_plan.total_transit_distance_km or 0.0
        transit_distance_km = base_transit if base_transit > 0 else transit_distance_calc

        total_minutes = int(round((cursor_time - initial_time).total_seconds() / 60.0))
        geometry_points = [(item.lat, item.lon) for item in route_items]

        return ItineraryResult(
            items=route_items,
            total_distance_km=total_distance_km,
            walking_distance_km=walking_distance_km,
            transit_distance_km=transit_distance_km,
            total_minutes=total_minutes,
            geometry_points=geometry_points,
            base_notes=base_notes,
        )

    def _spawn_geometry_task(
        self, start_ctx: StartContext, geometry_points: Sequence[Tuple[float, float]]
    ) -> Optional[asyncio.Task[route_pb2.RouteGeometryResponse]]:
        if not geometry_points:
            return None
        return asyncio.create_task(
            self.clients.route_planner_client.calculate_route_geometry(
                start_lat=start_ctx.lat,
                start_lon=start_ctx.lon,
                waypoints=geometry_points,
            )
        )

    async def _resolve_geometry(
        self,
        task: Optional[asyncio.Task[route_pb2.RouteGeometryResponse]],
        start_ctx: StartContext,
        geometry_points: Sequence[Tuple[float, float]],
    ) -> List[List[float]]:
        default_geometry = self._default_geometry(start_ctx, geometry_points)
        if not task:
            return default_geometry

        try:
            response = await task
        except Exception as exc:
            logger.warning("Failed to fetch detailed geometry: %s", exc)
            return default_geometry

        if response.geometry:
            return [[coord.lat, coord.lon] for coord in response.geometry]
        return default_geometry

    def _default_geometry(
        self, start_ctx: StartContext, geometry_points: Sequence[Tuple[float, float]]
    ) -> List[List[float]]:
        if not geometry_points:
            return [[start_ctx.lat, start_ctx.lon]]
        return [[start_ctx.lat, start_ctx.lon]] + [[lat, lon] for lat, lon in geometry_points]

    def _compute_time_warnings(
        self, request: RouteRequest, total_minutes: int
    ) -> List[str]:
        limit = int(request.hours * 60)
        if total_minutes > limit:
            return [
                "Маршрут получился чуть длиннее указанного времени — скорректируйте длительность или интересы."
            ]
        return []

    async def _maybe_add_coffee_break(
        self,
        preferences: CoffeePreferences,
        current_lat: float,
        current_lon: float,
        cursor_time: datetime,
        order_number: int,
        intensity: str,
    ) -> Optional[Tuple[POIInRoute, datetime, float, float, float]]:
        radius = preferences.search_radius_km or 0.6

        try:
            cafes = await self.clients.poi_client.find_cafes_near_location(
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
        walk_minutes = _minutes_from_distance(walk_km, intensity)
        arrival_time = cursor_time + timedelta(minutes=walk_minutes)

        stay_minutes = max(15, min(30, preferences.interval_minutes // 3))
        stay_minutes = _effective_visit_minutes(stay_minutes, intensity)
        leave_time = arrival_time + timedelta(minutes=stay_minutes)

        why = f"Сделайте паузу в {cafe.name}: уютное место неподалёку для кофе и отдыха."
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

    async def _safe_cancel(self, task: Optional[asyncio.Task[List[Any]]]) -> None:
        if not task:
            return
        if not task.done():
            task.cancel()
        with suppress(asyncio.CancelledError):
            try:
                await task
            except Exception:
                logger.debug("Prefetch task raised during cleanup", exc_info=True)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    a = sin(d_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(d_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return radius * c


def _get_intensity_profile(intensity: str) -> Dict[str, float]:
    return INTENSITY_PROFILES.get(intensity, INTENSITY_PROFILES["medium"])


def _minutes_from_distance(distance_km: float, intensity: str = "medium") -> float:
    if distance_km <= 0:
        return 0.0
    profile = _get_intensity_profile(intensity)
    walk_speed = max(0.5, WALK_SPEED_KMH * profile["walk_speed_multiplier"])
    return (distance_km / walk_speed) * 60.0


def _effective_visit_minutes(base_minutes: Optional[int], intensity: str) -> int:
    minutes = base_minutes or DEFAULT_VISIT_MINUTES
    profile = _get_intensity_profile(intensity)
    adjusted = int(round(minutes * profile["visit_duration_multiplier"]))
    min_minutes = int(profile["min_visit_minutes"])
    max_minutes = int(profile["max_visit_minutes"])
    return max(min_minutes, min(max_minutes, max(5, adjusted)))


def _convert_transit_stop(stop_msg: route_pb2.TransitStop) -> Optional[TransitStopInfo]:
    has_position = stop_msg.HasField("position")
    if not stop_msg.name and not stop_msg.side and not has_position:
        return None

    position = (
        CoordinatePoint(lat=stop_msg.position.lat, lon=stop_msg.position.lon)
        if has_position
        else None
    )

    return TransitStopInfo(
        name=stop_msg.name or "",
        side=stop_msg.side or None,
        position=position,
    )


def _convert_leg_proto(leg: route_pb2.RouteLeg) -> RouteLegInstruction:
    maneuvers: List[ManeuverInstruction] = []
    for step in leg.maneuvers:
        distance = step.distance_m if step.distance_m else None
        duration = step.duration_sec if step.duration_sec else None
        maneuvers.append(
            ManeuverInstruction(
                text=step.instruction or "",
                street_name=step.street_name or None,
                distance_m=distance,
                duration_sec=duration,
            )
        )

    transit: Optional[TransitGuidance] = None
    if leg.HasField("transit"):
        transit_msg = leg.transit
        transit = TransitGuidance(
            provider=transit_msg.provider or None,
            line_name=transit_msg.line_name or None,
            vehicle_type=transit_msg.vehicle_type or None,
            direction=transit_msg.direction or None,
            vehicle_number=transit_msg.vehicle_number or None,
            summary=transit_msg.summary or None,
            boarding=_convert_transit_stop(transit_msg.boarding),
            alighting=_convert_transit_stop(transit_msg.alighting),
            departure_time=transit_msg.departure_time or None,
            arrival_time=transit_msg.arrival_time or None,
            notes=transit_msg.notes or None,
            walk_to_board_meters=
                transit_msg.walk_to_board_meters if transit_msg.walk_to_board_meters else None,
            walk_from_alight_meters=
                transit_msg.walk_from_alight_meters if transit_msg.walk_from_alight_meters else None,
        )

    mode = leg.mode or ("transit" if transit else "walking")

    return RouteLegInstruction(
        mode=mode,
        start=CoordinatePoint(lat=leg.start.lat, lon=leg.start.lon),
        end=CoordinatePoint(lat=leg.end.lat, lon=leg.end.lon),
        distance_km=leg.distance_km,
        duration_minutes=leg.duration_minutes,
        maneuvers=maneuvers,
        transit=transit,
    )


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


def _fallback_summary(poi_names: Iterable[str]) -> str:
    names = [name for name in poi_names if name]
    if not names:
        return "Не удалось сформировать описание маршрута."
    joined = ", ".join(names)
    return f"Предлагаем прогулку по Нижнему Новгороду через точки: {joined}."


def _fallback_why(name: str, description: Optional[str]) -> str:
    base = (description or "Уникальная точка маршрута.").strip()
    return base if base else f"{name} — уникальная точка маршрута."


def _stable_coffee_id(source_id: Any) -> int:
    return abs(hash(source_id)) % 900_000 + 100_000
