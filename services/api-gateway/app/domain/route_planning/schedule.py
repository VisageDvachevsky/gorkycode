from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta
from typing import FrozenSet, List, Optional, Set, Tuple

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
    if value in {"24:00", "24:00:00"}:
        return dt_time(0, 0)
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


DAY_ALIASES = {
    "mo": 0,
    "mon": 0,
    "monday": 0,
    "пн": 0,
    "пон": 0,
    "понедельник": 0,
    "tu": 1,
    "tue": 1,
    "tues": 1,
    "tuesday": 1,
    "вт": 1,
    "вто": 1,
    "вторник": 1,
    "we": 2,
    "wed": 2,
    "wednesday": 2,
    "ср": 2,
    "сред": 2,
    "среда": 2,
    "th": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "thursday": 3,
    "чт": 3,
    "чет": 3,
    "четверг": 3,
    "fr": 4,
    "fri": 4,
    "friday": 4,
    "пт": 4,
    "пят": 4,
    "пятница": 4,
    "sa": 5,
    "sat": 5,
    "saturday": 5,
    "сб": 5,
    "суб": 5,
    "суббота": 5,
    "su": 6,
    "sun": 6,
    "sunday": 6,
    "вс": 6,
    "вос": 6,
    "воскресенье": 6,
    "ежедневно": -1,
    "daily": -1,
    "everyday": -1,
}


@dataclass(frozen=True)
class OpeningHoursWindow:
    days: FrozenSet[int]
    start: dt_time
    end: dt_time
    wraps: bool

    @property
    def duration_minutes(self) -> float:
        start_minutes = self.start.hour * 60 + self.start.minute
        end_minutes = self.end.hour * 60 + self.end.minute
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        return float(max(end_minutes - start_minutes, 0))


OPENING_RANGE_RE = re.compile(r"(?P<start>\d{1,2}:\d{2})\s*-\s*(?P<end>\d{1,2}:\d{2})")


def _parse_days(value: str) -> Set[int]:
    normalized = value.strip().lower()
    if not normalized:
        return set(range(7))
    normalized = normalized.replace("–", "-")
    if normalized in DAY_ALIASES and DAY_ALIASES[normalized] == -1:
        return set(range(7))

    days: Set[int] = set()
    for token in (part.strip() for part in normalized.split(",") if part.strip()):
        if "-" in token:
            start_token, end_token = (part.strip() for part in token.split("-", 1))
            start_idx = DAY_ALIASES.get(start_token)
            end_idx = DAY_ALIASES.get(end_token)
            if start_idx is None or end_idx is None:
                continue
            idx = start_idx
            days.add(idx)
            while idx != end_idx:
                idx = (idx + 1) % 7
                days.add(idx)
        else:
            idx = DAY_ALIASES.get(token)
            if idx is not None and idx >= 0:
                days.add(idx)
    if not days:
        return set(range(7))
    return days


def parse_opening_hours(expression: str) -> List[OpeningHoursWindow]:
    normalized = (expression or "").strip()
    if not normalized:
        return []

    normalized = normalized.replace("–", "-")
    segments: List[Tuple[FrozenSet[int], dt_time, dt_time, bool]] = []
    for part in normalized.split(";"):
        segment = part.strip()
        if not segment:
            continue
        lowered = segment.lower()
        if "off" in lowered or "closed" in lowered or "выход" in lowered:
            continue
        first_digit = next((idx for idx, ch in enumerate(segment) if ch.isdigit()), None)
        if first_digit is None:
            continue
        day_part = segment[:first_digit].strip()
        time_part = segment[first_digit:].strip()
        time_ranges = [item.strip() for item in time_part.split(",") if item.strip()]
        for time_range in time_ranges:
            match = OPENING_RANGE_RE.match(time_range)
            if not match:
                continue
            start_time = parse_time_string(match.group("start"))
            end_time = parse_time_string(match.group("end"))
            if start_time is None or end_time is None:
                continue
            wraps = (end_time.hour, end_time.minute) <= (start_time.hour, start_time.minute)
            days = _parse_days(day_part)
            segments.append(
                (
                    frozenset(days),
                    start_time,
                    end_time,
                    wraps,
                )
            )

    windows: List[OpeningHoursWindow] = []
    for days, start_time, end_time, wraps in segments:
        windows.append(OpeningHoursWindow(days=days, start=start_time, end=end_time, wraps=wraps))
    return windows


def _evaluate_opening_hours(expression: str, current_time: datetime, max_wait_minutes: int) -> Optional[Tuple[bool, Optional[float]]]:
    normalized = expression.strip().lower()
    compact = normalized.replace(" ", "")
    if "24/7" in compact or "24-7" in compact or "круглосуточ" in normalized:
        return True, 0.0

    windows = parse_opening_hours(expression)
    if not windows:
        return None

    weekday = current_time.weekday()
    best_wait: Optional[float] = None
    seen_today = False

    for window in windows:
        duration = window.duration_minutes
        if weekday in window.days:
            seen_today = True
            start_today = current_time.replace(
                hour=window.start.hour,
                minute=window.start.minute,
                second=0,
                microsecond=0,
            )
            end_today = start_today + timedelta(minutes=duration)
            if current_time < start_today:
                wait = (start_today - current_time).total_seconds() / 60.0
                if best_wait is None or wait < best_wait:
                    best_wait = wait
            elif current_time <= end_today:
                return True, 0.0

        if window.wraps:
            previous_day = (weekday - 1) % 7
            if previous_day in window.days:
                start_previous = (current_time - timedelta(days=1)).replace(
                    hour=window.start.hour,
                    minute=window.start.minute,
                    second=0,
                    microsecond=0,
                )
                end_previous = start_previous + timedelta(minutes=duration)
                if start_previous <= current_time <= end_previous:
                    return True, 0.0

    if best_wait is not None:
        if best_wait <= max_wait_minutes:
            return True, best_wait
        return False, best_wait

    if seen_today:
        return False, None

    return False, None


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


def is_open_at(
    poi,
    current_time: datetime,
    *,
    max_wait_minutes: int = 45,
) -> Tuple[bool, float]:
    raw_hours = getattr(poi, "opening_hours", None) or ""
    evaluation = None
    if raw_hours:
        evaluation = _evaluate_opening_hours(raw_hours, current_time, max_wait_minutes)
        if evaluation is not None:
            return evaluation[0], float(evaluation[1] or 0.0)

    open_time = getattr(poi, "open_time", None)
    close_time = getattr(poi, "close_time", None)
    _, _, is_open, _, _, wait_minutes = align_visit_with_schedule(
        current_time,
        visit_minutes=1.0,
        category=getattr(poi, "category", None),
        open_time=open_time,
        close_time=close_time,
    )
    wait_value = float(wait_minutes or 0.0)
    if not is_open:
        if wait_value > 0.0 and wait_value <= max_wait_minutes:
            return True, wait_value
        return False, wait_value
    if wait_value > max_wait_minutes:
        return False, wait_value
    return True, wait_value
