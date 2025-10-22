from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from app.core.config import settings
from app.grpc.clients import grpc_clients
from app.models.schemas import (
    CoordinatePoint,
    ManeuverInstruction,
    POIInRoute,
    RouteLegInstruction,
    RouteRequest,
    RouteResponse,
)
from app.proto import llm_pb2
from app.services.time_scheduler import time_scheduler

from .coffee import estimate_coffee_break_minutes, maybe_add_coffee_break, recommended_interval
from .elevation import ElevationService
from .exceptions import ExternalServiceError, RoutePlanningError
from .explanations import (
    build_profile_text,
    emoji_for_poi,
    fallback_summary,
    fallback_why,
    map_intensity_for_llm,
    map_intensity_for_ranking,
)
from .geometry import (
    LegEstimate,
    OSRMClient,
    TwoGISRoutingClient,
    haversine_km,
    minutes_from_distance,
)
from .intensity import (
    candidate_multiplier,
    effective_visit_minutes,
    min_visit_minutes_value,
    safety_buffer_minutes,
    target_visit_count,
    transition_padding,
)
from .models import CandidateScore, WeatherSnapshot
from .schedule import align_visit_with_schedule
from .scoring import (
    alternate_street_history_candidates,
    apply_time_window_filters,
    needs_street_history_mix,
    prefilter_candidates,
    prioritize_candidates,
)
from .sharing import generate_share_token
from .start_location import resolve_start_location
from .time_phase import resolve_time_phase
from .weather import load_weather_snapshot

logger = logging.getLogger(__name__)


@dataclass
class PlannedCandidate:
    id: int
    name: str
    lat: float
    lon: float
    avg_visit_minutes: int
    effective_visit_minutes: int
    rating: float
    category: Optional[str]
    description: Optional[str]
    tags: List[str]
    local_tip: Optional[str]
    address: Optional[str]
    open_time: Optional[str]
    close_time: Optional[str]
    selection_score: Optional[float]
    selection_penalty: Optional[float]
    selection_contextual: Optional[float]
    selection_distance: Optional[float]


class RoutePlanner:
    def __init__(self, request: RouteRequest) -> None:
        self.request = request
        self.start_lat: float = 0.0
        self.start_lon: float = 0.0
        self.start_label: str = ""
        self.weather_snapshot: Optional[WeatherSnapshot] = None
        self.profile_text: str = ""
        self.start_time: datetime
        self.scheduler_warnings: List[str] = []
        self.osrm_client = OSRMClient(settings.OSRM_BASE_URL)
        self.road_router = TwoGISRoutingClient(
            settings.TWOGIS_API_KEY,
            locale=settings.TWOGIS_LOCALE,
        )
        self.elevation_service = ElevationService(settings.ELEVATION_SERVICE_URL)

    async def plan(self) -> RouteResponse:
        self.start_lat, self.start_lon, self.start_label = await resolve_start_location(self.request)

        tz = self.request.resolved_timezone()
        time_plan = time_scheduler.determine_start_time(self.request.start_time, tz, self.request.hours)
        self.start_time = time_plan.start_time
        self.scheduler_warnings = list(time_plan.warnings)

        self.profile_text = build_profile_text(self.request)
        self.weather_snapshot = await load_weather_snapshot(
            self.start_lat, self.start_lon, self.request.intensity
        )

        user_embedding = await self._build_embedding()
        scored_pois = await self._rank_pois(user_embedding)

        filtered = apply_time_window_filters(scored_pois, self.start_time)
        if needs_street_history_mix(self.request):
            filtered = alternate_street_history_candidates(filtered)
        if not filtered:
            raise RoutePlanningError("Под ваши предпочтения не нашли подходящих мест", status_code=404)

        prefiltered = prefilter_candidates(
            filtered,
            start_lat=self.start_lat,
            start_lon=self.start_lon,
            intensity=self.request.intensity,
            max_candidates=60,
        )

        prioritized, score_map = prioritize_candidates(
            prefiltered,
            start_time=self.start_time,
            intensity=self.request.intensity,
            social_mode=self.request.social_mode,
            start_lat=self.start_lat,
            start_lon=self.start_lon,
            weather=self.weather_snapshot,
        )
        if not prioritized:
            raise RoutePlanningError("Не удалось подобрать подходящие точки маршрута", status_code=404)

        planned_candidates = await self._prepare_candidates(prioritized, score_map)
        if not planned_candidates:
            raise RoutePlanningError("Не удалось собрать информацию по точкам маршрута", status_code=404)

        route_items, movement_legs, geometry = await self._build_route(planned_candidates, score_map)

        summary, atmosphere, notes_from_llm = await self._build_llm_context(route_items)

        total_distance_km = sum(leg.distance_km for leg in movement_legs)
        walking_distance_km = total_distance_km

        if route_items:
            total_est_minutes = int(round((route_items[-1].leave_time - self.start_time).total_seconds() / 60.0))
        else:
            total_est_minutes = 0

        time_limit_minutes = int(self.request.hours * 60)
        warnings = list(self.scheduler_warnings)
        if total_est_minutes > time_limit_minutes:
            warnings.append(
                "Маршрут получился чуть длиннее указанного времени — скорректируйте длительность или интересы."
            )

        weather_advice = None
        if self.weather_snapshot and self.weather_snapshot.advice:
            highlight_name = next((poi.name for poi in route_items if not poi.is_coffee_break), None)
            advice_text = self.weather_snapshot.advice
            if highlight_name:
                advice_text = advice_text.rstrip(".") + f", но {highlight_name} всё равно впечатляет."
            weather_advice = advice_text

        notes = [f"Старт: {self.start_label}"]
        if self.scheduler_warnings:
            notes.extend(self.scheduler_warnings)
        safety_buffer = safety_buffer_minutes(self.request.intensity)
        if safety_buffer > 0:
            notes.append(
                f"Заложен буфер {int(round(safety_buffer))} мин на ориентирование и переходы"
            )
        visit_minutes_total = sum(poi.est_visit_minutes for poi in route_items if not poi.is_coffee_break)
        if visit_minutes_total >= 1:
            notes.append(
                f"На посещение точек — около {visit_minutes_total} мин чистого времени"
            )
        coffee_breaks = sum(1 for poi in route_items if poi.is_coffee_break)
        if coffee_breaks:
            if coffee_breaks == 1:
                notes.append("Запланирована кофейная пауза по вашим предпочтениям")
            else:
                notes.append(f"Запланированы {coffee_breaks} кофейные паузы по вашим предпочтениям")
        notes.extend(notes_from_llm)
        if weather_advice:
            notes.append(weather_advice)

        share_token = generate_share_token(
            summary,
            total_distance_km,
            total_est_minutes,
            [item.poi_id for item in route_items],
        )

        response = RouteResponse(
            summary=summary,
            route=route_items,
            total_est_minutes=total_est_minutes,
            total_distance_km=round(total_distance_km, 2),
            notes=notes,
            atmospheric_description=atmosphere,
            route_geometry=geometry,
            start_time_used=self.start_time,
            time_warnings=warnings,
            movement_legs=movement_legs,
            walking_distance_km=round(walking_distance_km, 2),
            transit_distance_km=0.0,
            weather_advice=weather_advice,
            share_token=share_token,
        )
        return response

    async def _build_embedding(self) -> List[float]:
        try:
            embedding_response = await grpc_clients.embedding_client.generate_embedding(
                text=self.profile_text or "Прогулка по Нижнему Новгороду",
                use_cache=True,
            )
        except Exception as exc:
            raise ExternalServiceError("Сервис эмбеддингов недоступен") from exc

        vector = list(embedding_response.vector)
        if not vector:
            raise ExternalServiceError("Не удалось построить профиль пользователя")
        return vector

    async def _rank_pois(self, user_embedding: List[float]):
        try:
            ranking_response = await grpc_clients.ranking_client.rank_pois(
                user_embedding=user_embedding,
                social_mode=self.request.social_mode,
                intensity=map_intensity_for_ranking(self.request.intensity),
                top_k=30,
                categories_filter=self.request.categories or [],
                start_time_minutes=self.start_time.hour * 60 + self.start_time.minute,
            )
        except Exception as exc:
            raise ExternalServiceError("Сервис ранжирования недоступен") from exc
        return list(ranking_response)

    async def _prepare_candidates(
        self,
        prioritized: Sequence[CandidateScore],
        score_map: Dict[int, CandidateScore],
    ) -> List[PlannedCandidate]:
        base_candidate_target = max(
            6, int(round(self.request.hours * candidate_multiplier(self.request.intensity)))
        )
        buffer = max(4, int(base_candidate_target * 0.4))
        candidate_limit = min(len(prioritized), base_candidate_target + buffer, 80)

        selected = prioritized[:candidate_limit]
        ranked_ids = [score.poi.poi_id for score in selected if getattr(score.poi, "poi_id", None)]
        categories = {
            getattr(score.poi, "category", None)
            for score in selected
            if getattr(score.poi, "category", None)
        }

        if selected:
            logger.info(
                "Categories in ranked result (raw): %s",
                [getattr(score.poi, "category", "unknown") or "unknown" for score in selected],
            )

        details: Dict[int, object] = {}
        if categories:
            try:
                poi_details = await grpc_clients.poi_client.get_all_pois(
                    categories=list(categories), with_embeddings=False
                )
                details = {poi.id: poi for poi in poi_details}
            except Exception as exc:
                logger.warning("Failed to fetch POI metadata: %s", exc)

        planned: List[PlannedCandidate] = []
        for score in selected:
            poi = score.poi
            poi_id = getattr(poi, "poi_id", None)
            if poi_id is None:
                continue
            detail = details.get(poi_id)
            base_visit = getattr(poi, "avg_visit_minutes", None) or 0
            effective_visit = effective_visit_minutes(base_visit or None, self.request.intensity)
            planned.append(
                PlannedCandidate(
                    id=poi_id,
                    name=getattr(poi, "name", "Без названия"),
                    lat=getattr(poi, "lat", 0.0),
                    lon=getattr(poi, "lon", 0.0),
                    avg_visit_minutes=base_visit or effective_visit,
                    effective_visit_minutes=effective_visit,
                    rating=getattr(poi, "rating", 0.0) or 0.0,
                    category=getattr(poi, "category", None),
                    description=getattr(poi, "description", None),
                    tags=list(getattr(poi, "tags", []) or []),
                    local_tip=getattr(detail, "local_tip", None),
                    address=getattr(detail, "address", None),
                    open_time=getattr(detail, "open_time", None) or getattr(poi, "open_time", None),
                    close_time=getattr(detail, "close_time", None) or getattr(poi, "close_time", None),
                    selection_score=score.final_score,
                    selection_penalty=score.penalty,
                    selection_contextual=score.contextual,
                    selection_distance=score.distance_km,
                )
            )
        return planned

    async def _build_route(
        self,
        candidates: List[PlannedCandidate],
        score_map: Dict[int, CandidateScore],
    ) -> Tuple[List[POIInRoute], List[RouteLegInstruction], List[List[float]]]:
        if not candidates:
            return [], [], [[self.start_lat, self.start_lon]]

        available_minutes = self._effective_minutes()
        target_goal = target_visit_count(self.request.hours, self.request.intensity)
        ordered, leftovers, scheduled_minutes = self._order_candidates(
            candidates, available_minutes, target_goal
        )
        if not ordered:
            raise RoutePlanningError(
                "Не удалось уместить точки в заданное время", status_code=404
            )
        if leftovers:
            logger.info(
                "⏳ Отложено кандидатов: %s (доступно ещё %.0f мин)",
                len(leftovers),
                max(0.0, available_minutes - scheduled_minutes),
            )

        movement_legs: List[RouteLegInstruction] = []
        route_items: List[POIInRoute] = []
        geometry_points: List[Tuple[float, float]] = [(self.start_lat, self.start_lon)]

        precomputed_legs = await self._compute_sequence_legs(ordered)

        cursor_time = self.start_time
        current_lat, current_lon = self.start_lat, self.start_lon
        order_counter = 1
        last_coffee_timestamp = cursor_time
        preferences = self.request.coffee_preferences
        interval = recommended_interval(self.request.intensity, preferences)
        for idx, candidate in enumerate(ordered):
            if idx < len(precomputed_legs):
                leg_estimate = precomputed_legs[idx]
            else:
                leg_estimate = await self._compute_leg((current_lat, current_lon), (candidate.lat, candidate.lon))
            cursor_time += timedelta(minutes=leg_estimate.duration_minutes)
            geometry_points.extend(leg_estimate.geometry[1:])
            movement_legs.append(self._leg_instruction(leg_estimate, (current_lat, current_lon), (candidate.lat, candidate.lon)))

            score_meta = score_map.get(candidate.id)
            visit_start, visit_end, is_open, opening_label, availability_note, wait_minutes = align_visit_with_schedule(
                cursor_time,
                candidate.effective_visit_minutes,
                candidate.category,
                candidate.open_time,
                candidate.close_time,
            )
            actual_visit_minutes = max(0.0, (visit_end - visit_start).total_seconds() / 60.0)
            leave_time = visit_end + timedelta(minutes=transition_padding(self.request.intensity))

            emoji = emoji_for_poi(candidate.category, candidate.tags)
            phase_hint = resolve_time_phase(visit_start)
            why = fallback_why(
                candidate.name,
                candidate.description,
                category=candidate.category,
                social_mode=self.request.social_mode,
                phase=phase_hint,
                contextual_score=score_meta.contextual if score_meta else None,
            )

            route_items.append(
                POIInRoute(
                    order=order_counter,
                    poi_id=candidate.id,
                    name=candidate.name,
                    lat=candidate.lat,
                    lon=candidate.lon,
                    why=why,
                    tip=candidate.local_tip,
                    est_visit_minutes=int(round(actual_visit_minutes)) or candidate.effective_visit_minutes,
                    arrival_time=visit_start,
                    leave_time=leave_time,
                    is_coffee_break=False,
                    is_open=is_open,
                    opening_hours=opening_label,
                    availability_note=availability_note,
                    category=candidate.category,
                    tags=list(candidate.tags),
                    emoji=emoji,
                    distance_from_previous_km=round(leg_estimate.distance_km, 2),
                )
            )

            cursor_time = leave_time
            current_lat, current_lon = candidate.lat, candidate.lon
            order_counter += 1

            if preferences and preferences.enabled:
                elapsed_since_break = (cursor_time - last_coffee_timestamp).total_seconds() / 60.0
                if elapsed_since_break >= interval * 0.95:
                    coffee_data = await maybe_add_coffee_break(
                        preferences=preferences,
                        current_lat=current_lat,
                        current_lon=current_lon,
                        cursor_time=cursor_time,
                        order_number=order_counter,
                        intensity=self.request.intensity,
                        fetch_cafes=self._fetch_cafes,
                    )
                    if coffee_data:
                        coffee_item, _, coffee_lat, coffee_lon, _ = coffee_data
                        prev_point = (route_items[-1].lat, route_items[-1].lon)
                        coffee_leg = await self._compute_leg(prev_point, (coffee_lat, coffee_lon))
                        arrival_time = cursor_time + timedelta(minutes=coffee_leg.duration_minutes)
                        stay_minutes = coffee_item.est_visit_minutes
                        leave_time = arrival_time + timedelta(
                            minutes=stay_minutes + transition_padding(self.request.intensity)
                        )

                        coffee_item = coffee_item.model_copy(
                            update={
                                "arrival_time": arrival_time,
                                "leave_time": leave_time,
                                "distance_from_previous_km": round(coffee_leg.distance_km, 2),
                            }
                        )

                        route_items.append(coffee_item)
                        geometry_points.extend(coffee_leg.geometry[1:])
                        movement_legs.append(self._leg_instruction(coffee_leg, prev_point, (coffee_lat, coffee_lon)))

                        cursor_time = leave_time
                        current_lat, current_lon = coffee_lat, coffee_lon
                        order_counter += 1
                        last_coffee_timestamp = leave_time

        route_items.sort(key=lambda item: item.order)
        movement_legs = movement_legs[: len(route_items)]

        geometry = [[lat, lon] for lat, lon in geometry_points]
        if route_items:
            logger.info(
                "🧭 Итоговый маршрут: %s",
                [
                    item.category or ("coffee_break" if item.is_coffee_break else "unknown")
                    for item in route_items
                ],
            )
        return route_items, movement_legs, geometry

    def _order_candidates(
        self,
        candidates: List[PlannedCandidate],
        available_minutes: float,
        target_goal: int,
    ) -> Tuple[List[PlannedCandidate], List[PlannedCandidate], float]:
        from .geometry import optimize_sequence

        if not candidates:
            return [], [], 0.0

        intensity = self.request.intensity
        pad = transition_padding(intensity)
        min_visit = float(min_visit_minutes_value(intensity))

        points = [(c.lat, c.lon) for c in candidates]
        order_indices = optimize_sequence((self.start_lat, self.start_lon), points)
        ordered_candidates = [candidates[idx] for idx in order_indices]

        selected: List[PlannedCandidate] = []
        skipped: List[PlannedCandidate] = []
        total_minutes = 0.0
        current_lat, current_lon = self.start_lat, self.start_lon

        def try_add(candidate: PlannedCandidate, *, allow_overflow: bool) -> bool:
            nonlocal total_minutes, current_lat, current_lon

            distance = haversine_km(current_lat, current_lon, candidate.lat, candidate.lon)
            travel_minutes = minutes_from_distance(distance)
            available_remaining = available_minutes - total_minutes
            if available_remaining < 0:
                available_remaining = 0.0

            visit_minutes = float(candidate.effective_visit_minutes)
            incremental = travel_minutes + visit_minutes + pad

            if incremental <= available_remaining:
                selected.append(candidate)
                total_minutes += incremental
                current_lat, current_lon = candidate.lat, candidate.lon
                return True

            remaining_after_travel = available_remaining - travel_minutes - pad
            if remaining_after_travel >= min_visit:
                trimmed_visit = min(visit_minutes, remaining_after_travel)
                candidate.effective_visit_minutes = int(round(trimmed_visit))
                visit_minutes = float(candidate.effective_visit_minutes)
                incremental = travel_minutes + visit_minutes + pad
                if incremental <= max(available_minutes - total_minutes, 0.0):
                    selected.append(candidate)
                    total_minutes += incremental
                    current_lat, current_lon = candidate.lat, candidate.lon
                    return True

            if allow_overflow and total_minutes + incremental <= available_minutes * 1.08:
                selected.append(candidate)
                total_minutes += incremental
                current_lat, current_lon = candidate.lat, candidate.lon
                return True

            return False

        for candidate in ordered_candidates:
            allow_overflow = not selected or len(selected) < target_goal
            if try_add(candidate, allow_overflow=allow_overflow):
                continue
            skipped.append(candidate)

        if not selected and ordered_candidates:
            first_candidate = ordered_candidates[0]
            try_add(first_candidate, allow_overflow=True)
            if first_candidate in skipped:
                skipped.remove(first_candidate)

        # attempt to reuse skipped candidates while time remains
        added = True
        while skipped and added and total_minutes < available_minutes * 0.98:
            added = False
            for idx, candidate in enumerate(list(skipped)):
                allow_overflow = len(selected) < target_goal
                if try_add(candidate, allow_overflow=allow_overflow):
                    skipped.pop(idx)
                    added = True
                    break

        if skipped and len(selected) < target_goal:
            for idx, candidate in enumerate(list(skipped)):
                if try_add(candidate, allow_overflow=True):
                    skipped.pop(idx)
                if len(selected) >= target_goal:
                    break

        balanced = self._rebalance_categories(selected)
        total_minutes, _ = self._sequence_usage(balanced)

        while balanced and total_minutes > available_minutes * 1.08:
            skipped.insert(0, balanced.pop())
            total_minutes, _ = self._sequence_usage(balanced)

        if balanced:
            logger.info(
                "Categories in ranked result: %s",
                [candidate.category or "unknown" for candidate in balanced],
            )
            logger.info(
                "⏱️ Планируем %s точек: %.0f мин из %.0f доступных (цель %s)",
                len(balanced),
                total_minutes,
                available_minutes,
                target_goal,
            )

        return balanced, skipped, total_minutes

    def _rebalance_categories(
        self, sequence: Sequence[PlannedCandidate]
    ) -> List[PlannedCandidate]:
        if len(sequence) < 2:
            return list(sequence)

        balanced = list(sequence)
        for idx in range(1, len(balanced)):
            prev_category = balanced[idx - 1].category or "unknown"
            current_category = balanced[idx].category or "unknown"
            if prev_category == current_category:
                swap_idx = None
                for candidate_index in range(idx + 1, len(balanced)):
                    candidate_category = balanced[candidate_index].category or "unknown"
                    if candidate_category != prev_category:
                        swap_idx = candidate_index
                        break
                if swap_idx is not None:
                    balanced[idx], balanced[swap_idx] = balanced[swap_idx], balanced[idx]
        return balanced

    def _sequence_usage(
        self, sequence: Sequence[PlannedCandidate]
    ) -> Tuple[float, float]:
        if not sequence:
            return 0.0, 0.0

        pad = transition_padding(self.request.intensity)
        total_minutes = 0.0
        total_distance = 0.0
        current_lat, current_lon = self.start_lat, self.start_lon

        for candidate in sequence:
            distance = haversine_km(current_lat, current_lon, candidate.lat, candidate.lon)
            travel_minutes = minutes_from_distance(distance)
            total_minutes += travel_minutes + float(candidate.effective_visit_minutes) + pad
            total_distance += distance
            current_lat, current_lon = candidate.lat, candidate.lon

        return total_minutes, total_distance

    def _effective_minutes(self) -> float:
        total_minutes = float(self.request.hours * 60)
        reserved_coffee = estimate_coffee_break_minutes(
            total_minutes,
            intensity=self.request.intensity,
            preferences=self.request.coffee_preferences,
        )
        safety_buffer = safety_buffer_minutes(self.request.intensity)
        effective_minutes = max(15.0, total_minutes - reserved_coffee - safety_buffer)
        return effective_minutes

    async def _compute_sequence_legs(self, candidates: List[PlannedCandidate]) -> List[LegEstimate]:
        if not candidates:
            return []

        legs: List[LegEstimate] = []
        cursor = (self.start_lat, self.start_lon)
        for candidate in candidates:
            leg = await self._compute_leg(cursor, (candidate.lat, candidate.lon))
            legs.append(leg)
            cursor = (candidate.lat, candidate.lon)
        return legs

    async def _compute_leg(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
    ) -> LegEstimate:
        leg: Optional[LegEstimate] = None

        if self.road_router.is_enabled():
            try:
                leg = await self.road_router.route_leg(start, end)
            except Exception as exc:
                logger.debug("2GIS routing failed, fallback to OSRM: %s", exc)
                leg = None

        if leg is None:
            try:
                legs, _ = await self.osrm_client.route(start, [end])
                leg = legs[0] if legs else None
            except Exception as exc:
                logger.debug("OSRM lookup failed, using haversine fallback: %s", exc)
                leg = None

        if leg is None:
            distance = haversine_km(start[0], start[1], end[0], end[1])
            minutes = minutes_from_distance(distance)
            leg = LegEstimate(
                distance_km=distance,
                duration_minutes=minutes,
                geometry=[start, end],
                maneuvers=[],
            )

        if self.elevation_service.is_enabled():
            try:
                delta = await self.elevation_service.elevation_delta(start, end)
            except Exception:
                delta = None
            if delta is not None:
                if delta > 15:
                    leg.duration_minutes *= 1.2
                elif delta < -15:
                    leg.duration_minutes *= 0.9
        return leg

    def _leg_instruction(
        self,
        leg: LegEstimate,
        start: Tuple[float, float],
        end: Tuple[float, float],
    ) -> RouteLegInstruction:
        maneuvers: List[ManeuverInstruction] = []
        for step in leg.maneuvers:
            maneuvers.append(
                ManeuverInstruction(
                    text=step.get("instruction") or "",
                    street_name=step.get("street_name"),
                    distance_m=step.get("distance"),
                    duration_sec=step.get("duration"),
                )
            )
        return RouteLegInstruction(
            mode="walking",
            start=self._coord(start),
            end=self._coord(end),
            distance_km=leg.distance_km,
            duration_minutes=leg.duration_minutes,
            maneuvers=maneuvers,
        )

    async def _fetch_cafes(self, lat: float, lon: float, radius: float):
        try:
            cafes = await grpc_clients.poi_client.find_cafes_near_location(lat=lat, lon=lon, radius_km=radius)
        except Exception as exc:
            logger.warning("Failed to query cafes: %s", exc)
            raise
        return cafes

    def _coord(self, point: Tuple[float, float]):
        return CoordinatePoint(lat=point[0], lon=point[1])

    async def _build_llm_context(
        self, route_items: List[POIInRoute]
    ) -> Tuple[str, Optional[str], List[str]]:
        if not route_items:
            return fallback_summary([]), None, []

        weather_parts: List[str] = []
        if self.weather_snapshot:
            if self.weather_snapshot.description:
                weather_parts.append(self.weather_snapshot.description.lower())
            if self.weather_snapshot.temperature_c is not None:
                weather_parts.append(f"{int(round(self.weather_snapshot.temperature_c))}°C")
            if self.weather_snapshot.is_precipitation:
                weather_parts.append("есть осадки")
            elif self.weather_snapshot.is_foggy:
                weather_parts.append("туман")

        llm_context_parts = [self.profile_text]
        llm_context_parts.append(
            f"Старт {self.start_time.strftime('%H:%M')}, длительность {self.request.hours:.1f} ч"
        )
        if weather_parts:
            llm_context_parts.append("Погода: " + ", ".join(weather_parts))

        llm_request = llm_pb2.RouteExplanationRequest(
            route=[
                llm_pb2.POIContext(
                    id=item.poi_id,
                    name=item.name,
                    description=item.tip or "",
                    category=item.category or "",
                    tags=item.tags,
                    local_tip=item.tip or "",
                )
                for item in route_items
                if not item.is_coffee_break
            ],
            user_interests=" | ".join(part for part in llm_context_parts if part),
            social_mode=self.request.social_mode,
            intensity=map_intensity_for_llm(self.request.intensity),
        )

        summary = fallback_summary([item.name for item in route_items if not item.is_coffee_break])
        atmosphere = None
        notes_from_llm: List[str] = []

        try:
            llm_response = await grpc_clients.llm_client.generate_route_explanation(llm_request)
        except Exception as exc:
            logger.warning("LLM service unavailable, falling back to static texts: %s", exc)
            llm_response = None

        if llm_response:
            summary = llm_response.summary or summary
            atmosphere = llm_response.atmospheric_description or None
            notes_from_llm = list(llm_response.notes)
            explanation_map = {exp.poi_id: exp for exp in llm_response.explanations}
            for item in route_items:
                if item.is_coffee_break:
                    continue
                explanation = explanation_map.get(item.poi_id)
                if explanation and explanation.why:
                    item.why = explanation.why
                if explanation and explanation.tip:
                    item.tip = explanation.tip
        return summary, atmosphere, notes_from_llm
