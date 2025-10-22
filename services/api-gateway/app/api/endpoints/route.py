from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, time as dt_time
from math import atan2, cos, radians, sin, sqrt
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import httpx

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.grpc.clients import grpc_clients
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
from app.services.time_scheduler import time_scheduler
from app.services.share_store import share_store

logger = logging.getLogger(__name__)

router = APIRouter()

WALK_SPEED_KMH = 4.5
DEFAULT_VISIT_MINUTES = 45

INTENSITY_PROFILES: Dict[str, Dict[str, float]] = {
    "relaxed": {
        "target_per_hour": 1.1,
        "default_visit_minutes": 55.0,
        "min_visit_minutes": 40.0,
        "max_visit_minutes": 90.0,
        "transition_padding": 8.0,
        "safety_buffer": 20.0,
    },
    "medium": {
        "target_per_hour": 1.6,
        "default_visit_minutes": 42.0,
        "min_visit_minutes": 30.0,
        "max_visit_minutes": 70.0,
        "transition_padding": 6.0,
        "safety_buffer": 15.0,
    },
    "intense": {
        "target_per_hour": 2.3,
        "default_visit_minutes": 30.0,
        "min_visit_minutes": 20.0,
        "max_visit_minutes": 55.0,
        "transition_padding": 4.0,
        "safety_buffer": 10.0,
    },
}

STREET_ART_HINTS: Sequence[str] = (
    "стрит",
    "street",
    "граффити",
    "мурал",
)
HISTORY_HINTS: Sequence[str] = (
    "истор",
    "history",
    "кремл",
    "усадьб",
)
MORNING_AVOID_KEYWORDS: Sequence[str] = (
    "кофе",
    "coffee",
    "кафе",
    "бар",
    "brunch",
)
NIGHT_UNSAFE_KEYWORDS: Sequence[str] = (
    "сквер",
    "тропа",
    "двор",
    "аллея",
    "парк",
)
NIGHT_PREFERRED_KEYWORDS: Sequence[str] = (
    "набереж",
    "кремл",
    "центр",
    "площад",
)
CATEGORY_STREET_ART: Sequence[str] = (
    "art_object",
    "mosaic",
    "decorative_art",
)
CATEGORY_HISTORY: Sequence[str] = (
    "museum",
    "monument",
    "memorial",
    "architecture",
    "religious_site",
    "sculpture",
)
EMOJI_BY_CATEGORY: Dict[str, str] = {
    "museum": "🏛",
    "monument": "🗿",
    "memorial": "🕯",
    "architecture": "🏰",
    "religious_site": "⛪",
    "sculpture": "🎭",
    "art_object": "🎨",
    "mosaic": "🧩",
    "decorative_art": "🖼",
    "park": "🌳",
}

TYPICAL_OPENING_HOURS: Dict[str, Tuple[dt_time, dt_time]] = {
    "museum": (dt_time(10, 0), dt_time(19, 0)),
    "art_object": (dt_time(9, 0), dt_time(21, 0)),
    "architecture": (dt_time(9, 0), dt_time(22, 0)),
    "religious_site": (dt_time(8, 0), dt_time(20, 0)),
    "park": (dt_time(0, 0), dt_time(23, 59)),
    "memorial": (dt_time(0, 0), dt_time(23, 59)),
    "monument": (dt_time(0, 0), dt_time(23, 59)),
    "viewpoint": (dt_time(9, 0), dt_time(22, 0)),
    "embankment": (dt_time(0, 0), dt_time(23, 59)),
    "cafe": (dt_time(8, 0), dt_time(23, 0)),
    "bar": (dt_time(12, 0), dt_time(2, 0)),
    "sculpture": (dt_time(9, 0), dt_time(22, 0)),
    "default": (dt_time(9, 0), dt_time(21, 0)),
}


@dataclass(frozen=True)
class _POIMetadata:
    keywords: Tuple[str, ...]
    category: str
    tags: Tuple[str, ...]


def _build_poi_metadata(poi) -> _POIMetadata:
    raw_tags = getattr(poi, "tags", []) or []
    normalized_tags = tuple(_normalize(tag) for tag in raw_tags if tag)
    normalized_name = _normalize(getattr(poi, "name", ""))
    keywords = tuple(value for value in (normalized_name, *normalized_tags) if value)
    category = _normalize(getattr(poi, "category", ""))
    return _POIMetadata(keywords=keywords, category=category, tags=normalized_tags)


def _resolve_start_reference(
    start_time: Optional[datetime], start_hour: Optional[int]
) -> Tuple[datetime, int]:
    reference = start_time or datetime.now()
    if start_hour is not None:
        normalized_hour = int(start_hour) % 24
        reference = reference.replace(
            hour=normalized_hour, minute=0, second=0, microsecond=0
        )
        return reference, normalized_hour
    return reference, reference.hour


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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


def _get_intensity_profile(intensity: str) -> Dict[str, float]:
    return INTENSITY_PROFILES.get(intensity, INTENSITY_PROFILES["medium"])


def _transition_padding(intensity: str) -> float:
    profile = _get_intensity_profile(intensity)
    return float(profile.get("transition_padding", 5.0))


def _safety_buffer(intensity: str) -> float:
    profile = _get_intensity_profile(intensity)
    return float(profile.get("safety_buffer", 0.0))


def _minutes_from_distance(distance_km: float) -> float:
    if distance_km <= 0:
        return 0.0
    walk_speed = max(0.5, WALK_SPEED_KMH)
    return (distance_km / walk_speed) * 60.0


def _effective_visit_minutes(base_minutes: Optional[int], intensity: str) -> int:
    profile = _get_intensity_profile(intensity)
    default_visit = profile["default_visit_minutes"]
    minutes = float(base_minutes or default_visit)
    adjusted = (minutes + default_visit) / 2.0 if base_minutes else default_visit
    min_minutes = profile["min_visit_minutes"]
    max_minutes = profile["max_visit_minutes"]
    bounded = max(min_minutes, min(max_minutes, adjusted))
    return int(round(max(5.0, bounded)))


def _normalize(text: Optional[str]) -> str:
    return (text or "").lower()


def _contains_keywords(
    values: Iterable[str],
    keywords: Sequence[str],
    *,
    pre_normalized: bool = False,
) -> bool:
    candidates = [value for value in values if value]
    if not pre_normalized:
        candidates = [_normalize(value) for value in candidates]
    for value in candidates:
        for keyword in keywords:
            if keyword in value:
                return True
    return False


def _parse_time_string(value: Optional[str]) -> Optional[dt_time]:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _resolve_schedule_window(
    category: Optional[str], open_time: Optional[str], close_time: Optional[str]
) -> Tuple[dt_time, dt_time, bool, bool]:
    normalized = (category or "").lower().strip()
    normalized = normalized.replace(" ", "_")
    fallback = TYPICAL_OPENING_HOURS.get(
        normalized, TYPICAL_OPENING_HOURS["default"]
    )

    parsed_open = _parse_time_string(open_time)
    parsed_close = _parse_time_string(close_time)
    precise = bool(open_time or close_time)

    open_dt = parsed_open or fallback[0]
    close_dt = parsed_close or fallback[1]
    wraps = (close_dt.hour * 60 + close_dt.minute) <= (open_dt.hour * 60 + open_dt.minute)
    return open_dt, close_dt, precise, wraps


def _format_opening_label(
    open_time: dt_time, close_time: dt_time, wraps: bool, precise: bool
) -> str:
    open_label = open_time.strftime("%H:%M")
    close_label = close_time.strftime("%H:%M")
    wrap_suffix = " (+1 день)" if wraps else ""
    precision_suffix = " (точное)" if precise else " (ориентировочно)"
    return f"{open_label}–{close_label}{wrap_suffix}{precision_suffix}"


def _availability_score_for_start(poi, start_time: datetime) -> float:
    open_dt, close_dt, precise, wraps = _resolve_schedule_window(
        getattr(poi, "category", None),
        getattr(poi, "open_time", ""),
        getattr(poi, "close_time", ""),
    )

    start_minutes = start_time.hour * 60 + start_time.minute
    open_minutes = open_dt.hour * 60 + open_dt.minute
    close_minutes = close_dt.hour * 60 + close_dt.minute

    if wraps:
        close_minutes += 24 * 60
        if start_minutes <= close_minutes - 24 * 60:
            start_minutes += 24 * 60

    if open_minutes <= start_minutes <= close_minutes:
        return 1.0 if precise else 0.92
    if start_minutes < open_minutes:
        diff = open_minutes - start_minutes
        if diff <= 45:
            return 0.85
        if diff <= 120:
            return 0.72
        return 0.5

    diff = start_minutes - close_minutes
    if diff <= 45:
        return 0.68
    return 0.45


def _align_visit_with_schedule(
    arrival: datetime,
    visit_minutes: float,
    category: Optional[str],
    open_time: Optional[str],
    close_time: Optional[str],
) -> Tuple[datetime, datetime, bool, str, Optional[str], float]:
    open_dt, close_dt, precise, wraps = _resolve_schedule_window(
        category, open_time, close_time
    )

    day_start = arrival.replace(hour=0, minute=0, second=0, microsecond=0)
    arrival_minutes = (arrival - day_start).total_seconds() / 60.0
    open_minutes = open_dt.hour * 60 + open_dt.minute
    close_minutes = close_dt.hour * 60 + close_dt.minute

    if wraps:
        close_minutes += 24 * 60
        if arrival_minutes <= close_minutes - 24 * 60:
            arrival_minutes += 24 * 60

    wait_minutes = 0.0
    if arrival_minutes < open_minutes:
        wait_minutes = open_minutes - arrival_minutes
        arrival_minutes = open_minutes

    visit_end_minutes = arrival_minutes + visit_minutes
    is_open = visit_end_minutes <= close_minutes
    if not is_open:
        visit_end_minutes = min(visit_end_minutes, close_minutes)

    visit_start_time = day_start + timedelta(minutes=arrival_minutes)
    visit_end_time = day_start + timedelta(minutes=visit_end_minutes)
    opening_label = _format_opening_label(open_dt, close_dt, wraps, precise)

    note: Optional[str] = None
    if wait_minutes >= 1.0:
        note = f"Ждём открытия до {open_dt.strftime('%H:%M')}"
    if not is_open:
        closing_label = close_dt.strftime("%H:%M")
        closing_note = f"Место закрывается в {closing_label} — планируйте быстрее"
        note = f"{note}, {closing_note}" if note else closing_note

    return visit_start_time, visit_end_time, is_open, opening_label, note, wait_minutes


def _apply_time_window_filters(
    pois: Sequence,
    start_time: Optional[datetime] = None,
    *,
    start_hour: Optional[int] = None,
) -> List:
    entries = list(pois)
    if not entries:
        return entries

    resolved_start, resolved_hour = _resolve_start_reference(start_time, start_hour)
    metadata_entries = [(poi, _build_poi_metadata(poi)) for poi in entries]

    filtered_entries: List[Tuple[object, _POIMetadata]] = []
    for poi, meta in metadata_entries:
        if resolved_hour < 9 and _contains_keywords(
            meta.keywords, MORNING_AVOID_KEYWORDS, pre_normalized=True
        ):
            continue
        if resolved_hour >= 21 and _contains_keywords(
            meta.keywords, NIGHT_UNSAFE_KEYWORDS, pre_normalized=True
        ):
            continue
        filtered_entries.append((poi, meta))

    if not filtered_entries:
        filtered_entries = metadata_entries

    scored: List[Tuple[float, float, object]] = []
    for poi, meta in filtered_entries:
        base_score = _availability_score_for_start(poi, resolved_start)
        preference_bonus = 0.0
        if resolved_hour >= 21 and _contains_keywords(
            meta.keywords, NIGHT_PREFERRED_KEYWORDS, pre_normalized=True
        ):
            preference_bonus = 0.08
        rating = float(getattr(poi, "rating", 0.0) or 0.0)
        scored.append((min(1.1, base_score + preference_bonus), rating, poi))

    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [entry[2] for entry in scored]


def _is_street_art_meta(meta: _POIMetadata) -> bool:
    if meta.category in CATEGORY_STREET_ART:
        return True
    return _contains_keywords(meta.keywords, STREET_ART_HINTS, pre_normalized=True)


def _is_history_meta(meta: _POIMetadata) -> bool:
    if meta.category in CATEGORY_HISTORY:
        return True
    return _contains_keywords(meta.keywords, HISTORY_HINTS, pre_normalized=True)


def _is_street_art_candidate(poi) -> bool:
    return _is_street_art_meta(_build_poi_metadata(poi))


def _is_history_candidate(poi) -> bool:
    return _is_history_meta(_build_poi_metadata(poi))


def _alternate_street_history_candidates(pois: Sequence) -> List:
    entries = list(pois)
    metadata_entries = [(poi, _build_poi_metadata(poi)) for poi in entries]

    street_items = [poi for poi, meta in metadata_entries if _is_street_art_meta(meta)]
    history_items = [poi for poi, meta in metadata_entries if _is_history_meta(meta)]

    if not street_items or not history_items:
        return entries

    street_ids = {id(poi) for poi in street_items}
    history_ids = {id(poi) for poi in history_items}
    other_items = [
        poi
        for poi, _ in metadata_entries
        if id(poi) not in street_ids and id(poi) not in history_ids
    ]

    street_queue = street_items.copy()
    history_queue = history_items.copy()
    result: List = []
    take_history = len(history_queue) >= len(street_queue)

    while street_queue or history_queue:
        if take_history and history_queue:
            result.append(history_queue.pop(0))
        elif street_queue:
            result.append(street_queue.pop(0))
        elif history_queue:
            result.append(history_queue.pop(0))
        take_history = not take_history

    positions = {id(poi): index for index, poi in enumerate(entries)}

    for item in other_items:
        inserted = False
        for index, existing in enumerate(result):
            if positions[id(existing)] > positions[id(item)]:
                result.insert(index, item)
                inserted = True
                break
        if not inserted:
            result.append(item)

    return result


def _needs_street_history_mix(request: RouteRequest) -> bool:
    interests = [request.interests or ""]
    if request.categories:
        interests.extend(request.categories)
    combined = " ".join(interests).lower()
    return (
        any(keyword in combined for keyword in STREET_ART_HINTS)
        and any(keyword in combined for keyword in HISTORY_HINTS)
    )


def _emoji_for_poi(category: Optional[str], tags: Iterable[str], fallback: str = "📍") -> str:
    category_key = _normalize(category)
    if category_key in EMOJI_BY_CATEGORY:
        return EMOJI_BY_CATEGORY[category_key]
    normalized_tags = [_normalize(tag) for tag in tags if tag]
    if _contains_keywords(
        normalized_tags, STREET_ART_HINTS, pre_normalized=True
    ):
        return "🎨"
    if _contains_keywords(
        normalized_tags, HISTORY_HINTS, pre_normalized=True
    ):
        return "🏛"
    return fallback


def _generate_share_token(
    summary: str, distance: float, minutes: int, poi_ids: Sequence[int]
) -> str:
    payload = {
        "s": summary,
        "d": round(distance, 2),
        "t": minutes,
        "p": list(poi_ids),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


async def _fetch_weather_advice(
    lat: float,
    lon: float,
    highlight: Optional[str],
    intensity: str,
) -> Optional[str]:
    url = f"https://wttr.in/{lat},{lon}"
    params = {"format": "j1"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
    except Exception as exc:
        logger.debug("Weather lookup skipped: %s", exc)
        return None

    try:
        payload = response.json()
        current_block = (payload.get("current_condition") or [None])[0] or {}
        description = (
            (current_block.get("weatherDesc") or [{}])[0].get("value", "")
        ).strip()
        temp_raw = current_block.get("temp_C") or current_block.get("tempC")
        precip_raw = current_block.get("precipMM") or current_block.get("precip_mm")
        wind_raw = current_block.get("windspeedKmph") or current_block.get("windspeed_kmph")
    except Exception as exc:
        logger.debug("Weather payload parsing failed: %s", exc)
        return None

    temp_value: Optional[float]
    try:
        temp_value = float(temp_raw)
    except (TypeError, ValueError):
        temp_value = None

    try:
        precip_value = float(precip_raw)
    except (TypeError, ValueError):
        precip_value = 0.0

    try:
        wind_value = float(wind_raw)
    except (TypeError, ValueError):
        wind_value = 0.0

    fragments: List[str] = []

    if precip_value >= 1.0:
        fragments.append("Сегодня дождливо — возьмите зонт")
    elif precip_value > 0.1:
        fragments.append("Возможен лёгкий дождь, захватите ветровку")
    elif wind_value >= 25:
        fragments.append("На улице ветрено, планируйте уютные остановки")
    elif description:
        fragments.append(description.lower().capitalize())
    else:
        fragments.append("Погода располагает к прогулке")

    clothing: List[str] = []

    if temp_value is not None:
        temp_label = int(round(temp_value))
        fragments.append(f"температура около {temp_label}°C")
        if temp_label <= -10:
            clothing.append("очень тёплую куртку и термоперчатки")
        elif temp_label <= 0:
            clothing.append("слоистую одежду и шапку")
        elif temp_label <= 10:
            clothing.append("ветровку или лёгкое пальто")
        elif temp_label >= 24:
            clothing.append("дышащую одежду и головной убор")

    if precip_value >= 0.3:
        clothing.append("непромокаемую обувь")

    if intensity in {"intense", "high"}:
        clothing.append("удобные кроссовки и лёгкий рюкзак для воды")
    elif intensity in {"medium", "relaxed", "low"}:
        clothing.append("комфортную обувь для долгой прогулки")

    if clothing:
        fragments.append("одежда: " + ", ".join(clothing))

    if highlight:
        fragments.append(f"но {highlight} всё равно впечатляет")

    return ", ".join(fragments) + "."


def _estimate_coffee_break_minutes(
    total_minutes: float,
    intensity: str,
    preferences: Optional[CoffeePreferences],
) -> float:
    if not preferences or not preferences.enabled or total_minutes <= 0:
        return 0.0
    interval = max(30, preferences.interval_minutes)
    if total_minutes < interval:
        return 0.0
    breaks = int(total_minutes // interval)
    if breaks <= 0:
        return 0.0
    base_stay = max(15, min(30, interval // 3))
    stay_minutes = _effective_visit_minutes(base_stay, intensity)
    return float(breaks * stay_minutes)


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
    intensity: str,
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
    stay_minutes = _effective_visit_minutes(stay_minutes, intensity)
    padding = _transition_padding(intensity)
    leave_time = arrival_time + timedelta(minutes=stay_minutes + padding)

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
        category="coffee_break",
        tags=["coffee", "break"],
        emoji="☕",
        distance_from_previous_km=round(walk_km, 2),
    )

    return coffee_item, leave_time, cafe.lat, cafe.lon, walk_km


@router.post("/plan", response_model=RouteResponse)
async def plan_route(request: RouteRequest) -> RouteResponse:

    start_lat, start_lon, start_label = await _resolve_start_location(request)
    tz = request.resolved_timezone()

    time_plan = time_scheduler.determine_start_time(
        request.start_time, tz, request.hours
    )
    start_time = time_plan.start_time
    scheduler_warnings = time_plan.warnings

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
            start_time_minutes=start_time.hour * 60 + start_time.minute,
        )
    except Exception as exc:
        logger.exception("Ranking service error")
        raise HTTPException(503, "Сервис ранжирования недоступен") from exc

    scored_pois = list(ranking_response)
    scored_pois = _apply_time_window_filters(scored_pois, start_time)
    if _needs_street_history_mix(request):
        scored_pois = _alternate_street_history_candidates(scored_pois)
    if not scored_pois:
        raise HTTPException(404, "Под ваши предпочтения не нашли подходящих мест")

    total_available_minutes = float(request.hours * 60)
    reserved_coffee_minutes = _estimate_coffee_break_minutes(
        total_minutes=total_available_minutes,
        intensity=request.intensity,
        preferences=request.coffee_preferences,
    )
    safety_buffer = _safety_buffer(request.intensity)
    effective_minutes = max(
        15.0, total_available_minutes - reserved_coffee_minutes - safety_buffer
    )
    effective_hours = effective_minutes / 60.0

    coffee_break_targets = 0
    if request.coffee_preferences and request.coffee_preferences.enabled:
        interval = max(30, request.coffee_preferences.interval_minutes)
        if total_available_minutes >= interval:
            coffee_break_targets = int(total_available_minutes // interval)
            if coffee_break_targets <= 0 and reserved_coffee_minutes > 0:
                coffee_break_targets = 1

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
            available_hours=effective_hours,
            intensity=request.intensity,
        )
    except Exception as exc:
        logger.exception("Route planner error")
        raise HTTPException(503, "Сервис построения маршрутов недоступен") from exc

    if not route_plan.optimized_route:
        raise HTTPException(404, "Не удалось построить маршрут в заданное время")

    ordered_infos: List[route_pb2.POIInfo] = list(route_plan.optimized_route)
    ranked_by_id = {poi.poi_id: poi for poi in scored_pois}

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
        base_visit = poi_info.avg_visit_minutes or DEFAULT_VISIT_MINUTES
        effective_visit = _effective_visit_minutes(base_visit, request.intensity)
        ordered.append(
            {
                "id": poi_id,
                "name": poi_info.name,
                "lat": poi_info.lat,
                "lon": poi_info.lon,
                "avg_visit_minutes": base_visit,
                "effective_visit_minutes": effective_visit,
                "rating": ranked.rating or 0.0,
                "category": ranked.category,
                "description": ranked.description,
                "tags": list(ranked.tags),
                "local_tip": getattr(details, "local_tip", None),
                "address": getattr(details, "address", ""),
                "open_time": getattr(details, "open_time", "")
                or getattr(ranked, "open_time", ""),
                "close_time": getattr(details, "close_time", "")
                or getattr(ranked, "close_time", ""),
            }
        )

    if not ordered:
        raise HTTPException(404, "Не удалось собрать информацию по точкам маршрута")

    if coffee_break_targets and ordered:
        limit = max(1, len(ordered) // 2) if len(ordered) > 2 else 1
        coffee_break_targets = min(coffee_break_targets, limit)

    movement_leg_msgs = list(route_plan.legs)
    movement_legs: List[RouteLegInstruction] = [
        _convert_leg_proto(leg_msg) for leg_msg in movement_leg_msgs
    ]

    planned_distance_km = route_plan.total_distance_km or sum(
        leg.distance_km for leg in movement_legs
    )
    walking_distance_km = route_plan.total_walking_distance_km or sum(
        leg.distance_km for leg in movement_legs if leg.mode == "walking"
    )
    transit_distance_km = route_plan.total_transit_distance_km or sum(
        leg.distance_km for leg in movement_legs if leg.mode == "transit"
    )
    transit_distance_km = transit_distance_km or 0.0

    if movement_legs and len(movement_legs) != len(ordered):
        logger.warning(
            "Mismatch between movement legs (%s) and POIs (%s)",
            len(movement_legs),
            len(ordered),
        )

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
    extra_walking_km = 0.0
    route_items: List[POIInRoute] = []
    initial_time = start_time
    current_lat, current_lon = start_lat, start_lon
    order_counter = 1
    coffee_breaks_planned = 0
    last_coffee_timestamp = initial_time
    transition_padding = _transition_padding(request.intensity)
    visit_minutes_total = 0.0
    total_wait_minutes = 0.0

    for idx, item in enumerate(ordered):
        leg_distance = None
        leg_duration = None

        if idx < len(movement_legs):
            leg_info = movement_legs[idx]
            leg_distance = leg_info.distance_km
            leg_duration = leg_info.duration_minutes
        else:
            logger.debug("No precomputed leg for segment %s, using haversine", idx)

        if leg_distance is None:
            leg_distance = _haversine_km(current_lat, current_lon, item["lat"], item["lon"])
        if leg_duration is None:
            leg_duration = _minutes_from_distance(leg_distance)

        travel_minutes = float(leg_duration or 0.0)
        if travel_minutes:
            cursor_time += timedelta(minutes=travel_minutes)
        total_distance_km += leg_distance

        explanation = explanation_map.get(item["id"])
        planned_visit_minutes = item.get("effective_visit_minutes") or _effective_visit_minutes(
            item.get("avg_visit_minutes"), request.intensity
        )

        (
            visit_start,
            visit_end,
            is_open,
            opening_label,
            availability_note,
            wait_minutes,
        ) = _align_visit_with_schedule(
            cursor_time,
            planned_visit_minutes,
            item.get("category"),
            item.get("open_time"),
            item.get("close_time"),
        )

        actual_visit_minutes = max(
            0.0, (visit_end - visit_start).total_seconds() / 60.0
        )
        display_visit_minutes = (
            int(round(actual_visit_minutes))
            if actual_visit_minutes >= 5.0
            else int(round(planned_visit_minutes))
        )

        total_wait_minutes += wait_minutes
        visit_minutes_total += actual_visit_minutes

        leave_time = visit_end + timedelta(minutes=transition_padding)

        route_items.append(
            POIInRoute(
                order=order_counter,
                poi_id=item["id"],
                name=item["name"],
                lat=item["lat"],
                lon=item["lon"],
                why=(
                    explanation.why
                    if explanation and explanation.why
                    else _fallback_why(item["name"], item["description"])
                ),
                tip=(
                    explanation.tip
                    if explanation and explanation.tip
                    else (item.get("local_tip") or "")
                ),
                est_visit_minutes=display_visit_minutes,
                arrival_time=visit_start,
                leave_time=leave_time,
                is_coffee_break=False,
                is_open=is_open,
                opening_hours=opening_label,
                availability_note=availability_note,
                category=item.get("category"),
                tags=item.get("tags", []),
                emoji=_emoji_for_poi(item.get("category"), item.get("tags", [])),
                distance_from_previous_km=round(leg_distance, 2),
            )
        )

        cursor_time = leave_time
        current_lat, current_lon = item["lat"], item["lon"]
        order_counter += 1

        if (
            request.coffee_preferences
            and request.coffee_preferences.enabled
            and coffee_breaks_planned < coffee_break_targets
        ):
            elapsed_since_break = (
                cursor_time - last_coffee_timestamp
            ).total_seconds() / 60.0
            if elapsed_since_break >= request.coffee_preferences.interval_minutes:
                coffee_data = await _maybe_add_coffee_break(
                    preferences=request.coffee_preferences,
                    current_lat=current_lat,
                    current_lon=current_lon,
                    cursor_time=cursor_time,
                    order_number=order_counter,
                    intensity=request.intensity,
                )
                if coffee_data:
                    coffee_item, new_cursor_time, coffee_lat, coffee_lon, walk_km_to_cafe = coffee_data
                    total_distance_km += walk_km_to_cafe
                    walking_distance_km += walk_km_to_cafe
                    extra_walking_km += walk_km_to_cafe
                    route_items.append(coffee_item)
                    cursor_time = new_cursor_time
                    current_lat, current_lon = coffee_lat, coffee_lon
                    order_counter += 1
                    coffee_breaks_planned += 1
                    last_coffee_timestamp = new_cursor_time

    if planned_distance_km and total_distance_km < planned_distance_km:
        total_distance_km = planned_distance_km

    if walking_distance_km:
        walking_distance_km += extra_walking_km
    else:
        walking_distance_km = extra_walking_km

    total_est_minutes = int(round((cursor_time - initial_time).total_seconds() / 60.0))

    geometry_points = [(item.lat, item.lon) for item in route_items]
    if geometry_points:
        try:
            geometry_response = await grpc_clients.route_planner_client.calculate_route_geometry(
                start_lat=start_lat,
                start_lon=start_lon,
                waypoints=geometry_points,
            )
            if geometry_response.geometry:
                route_geometry = [
                    [coord.lat, coord.lon] for coord in geometry_response.geometry
                ]
            else:
                route_geometry = [[start_lat, start_lon]] + [
                    [lat, lon] for lat, lon in geometry_points
                ]
        except Exception as exc:
            logger.warning("Failed to fetch detailed geometry: %s", exc)
            route_geometry = [[start_lat, start_lon]] + [
                [lat, lon] for lat, lon in geometry_points
            ]
    else:
        route_geometry = [[start_lat, start_lon]]

    highlight_name = next(
        (poi.name for poi in route_items if not poi.is_coffee_break),
        None,
    )
    weather_advice = await _fetch_weather_advice(
        start_lat,
        start_lon,
        highlight_name,
        request.intensity,
    )

    notes: List[str] = [f"Старт: {start_label}"]
    if scheduler_warnings:
        notes.extend(scheduler_warnings)
    if safety_buffer > 0:
        notes.append(
            f"Заложен буфер {int(round(safety_buffer))} мин на ориентирование и переходы"
        )
    if visit_minutes_total >= 1.0:
        notes.append(
            f"На посещение точек — около {int(round(visit_minutes_total))} мин чистого времени"
        )
    if coffee_breaks_planned:
        if coffee_breaks_planned == 1:
            notes.append("Запланирована кофейная пауза по вашим предпочтениям")
        else:
            notes.append(
                f"Запланированы {coffee_breaks_planned} кофейные паузы по вашим предпочтениям"
            )
    if total_wait_minutes >= 1.0:
        notes.append(
            f"Учтём ожидание открытия площадок: около {int(round(total_wait_minutes))} мин"
        )
    notes.extend(notes_from_llm)
    if weather_advice:
        notes.append(weather_advice)

    time_limit_minutes = int(request.hours * 60)
    warnings: List[str] = list(scheduler_warnings)
    if total_est_minutes > time_limit_minutes:
        warnings.append(
            "Маршрут получился чуть длиннее указанного времени — скорректируйте длительность или интересы."
        )

    share_token = _generate_share_token(
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
        route_geometry=route_geometry,
        start_time_used=initial_time,
        time_warnings=warnings,
        movement_legs=movement_legs,
        walking_distance_km=round(walking_distance_km, 2),
        transit_distance_km=round(transit_distance_km, 2),
        weather_advice=weather_advice,
        share_token=share_token,
    )

    await share_store.save_route(
        share_token,
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
