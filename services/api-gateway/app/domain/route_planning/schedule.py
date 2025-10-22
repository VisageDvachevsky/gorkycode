from __future__ import annotations

from datetime import datetime, time as dt_time, timedelta
from typing import Optional, Tuple

from .constants import TYPICAL_OPENING_HOURS


def resolve_start_reference(
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


def parse_time_string(value: Optional[str]) -> Optional[dt_time]:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def resolve_schedule_window(
    category: Optional[str], open_time: Optional[str], close_time: Optional[str]
) -> Tuple[dt_time, dt_time, bool, bool]:
    normalized = (category or "").lower().strip().replace(" ", "_")
    fallback = TYPICAL_OPENING_HOURS.get(normalized, TYPICAL_OPENING_HOURS["default"])

    parsed_open = parse_time_string(open_time)
    parsed_close = parse_time_string(close_time)
    precise = bool(open_time or close_time)

    open_dt = parsed_open or fallback[0]
    close_dt = parsed_close or fallback[1]
    wraps = (close_dt.hour * 60 + close_dt.minute) <= (open_dt.hour * 60 + open_dt.minute)
    return open_dt, close_dt, precise, wraps


def format_opening_label(open_time: dt_time, close_time: dt_time, wraps: bool, precise: bool) -> str:
    open_label = open_time.strftime("%H:%M")
    close_label = close_time.strftime("%H:%M")
    wrap_suffix = " (+1 день)" if wraps else ""
    precision_suffix = " (точное)" if precise else " (ориентировочно)"
    return f"{open_label}–{close_label}{wrap_suffix}{precision_suffix}"


def availability_score_for_start(poi, start_time: datetime) -> float:
    open_dt, close_dt, precise, wraps = resolve_schedule_window(
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


def align_visit_with_schedule(
    arrival: datetime,
    visit_minutes: float,
    category: Optional[str],
    open_time: Optional[str],
    close_time: Optional[str],
) -> Tuple[datetime, datetime, bool, str, Optional[str], float]:
    open_dt, close_dt, precise, wraps = resolve_schedule_window(category, open_time, close_time)

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
    opening_label = format_opening_label(open_dt, close_dt, wraps, precise)

    note: Optional[str] = None
    if wait_minutes >= 1.0:
        note = f"Ждём открытия до {open_dt.strftime('%H:%M')}"
    if not is_open:
        closing_label = close_dt.strftime("%H:%M")
        closing_note = f"Место закрывается в {closing_label} — планируйте быстрее"
        note = f"{note}, {closing_note}" if note else closing_note

    return visit_start_time, visit_end_time, is_open, opening_label, note, wait_minutes
