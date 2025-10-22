from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from zoneinfo import ZoneInfo


@dataclass
class TimeSuggestion:
    start_time: datetime
    warnings: List[str]


class TimeScheduler:

    REASONABLE_START_HOURS: Tuple[int, int] = (9, 22)

    def determine_start_time(
        self,
        requested_time: Optional[str],
        tz: ZoneInfo,
        duration_hours: float,
        *,
        now: Optional[datetime] = None,
    ) -> TimeSuggestion:

        now_local = now or datetime.now(tz)
        warnings: List[str] = []

        if requested_time:
            parsed = self._parse_requested_time(requested_time, now_local)
            if parsed is not None:
                start_time, parsed_warnings = parsed
                warnings.extend(parsed_warnings)
                if not self._fits_reasonable_window(start_time, duration_hours):
                    suggested = self._suggest_reasonable_time(start_time, duration_hours)
                    warnings.append(
                        "Запрошенное время выходит за комфортные часы города — предлагаю сдвинуть старт на "
                        f"{suggested.strftime('%H:%M')}"
                    )
                return TimeSuggestion(start_time=start_time, warnings=warnings)
            warnings.append(
                "Не удалось разобрать указанное время старта — выбираю ближайшее комфортное окно"
            )

        if self._fits_reasonable_window(now_local, duration_hours):
            if self.REASONABLE_START_HOURS[0] <= now_local.hour < self.REASONABLE_START_HOURS[1]:
                return TimeSuggestion(start_time=now_local, warnings=warnings)

        suggested = self._suggest_reasonable_time(now_local, duration_hours)
        if now_local.hour < self.REASONABLE_START_HOURS[0]:
            warnings.append(
                f"Город ещё просыпается. Маршрут начнётся в {suggested.strftime('%H:%M')}"
            )
        elif now_local.hour >= self.REASONABLE_START_HOURS[1]:
            warnings.append(
                f"Сейчас поздновато для прогулки. Запланируем старт на {suggested.strftime('%H:%M')}"
            )
        else:
            warnings.append(
                f"Маршрут займёт больше времени, чем осталось сегодня — лучше начать в {suggested.strftime('%H:%M')}"
            )
        return TimeSuggestion(start_time=suggested, warnings=warnings)

    def _parse_requested_time(
        self, value: str, now_local: datetime
    ) -> Optional[Tuple[datetime, List[str]]]:
        try:
            hour, minute = map(int, value.split(":"))
        except ValueError:
            return None

        requested = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        warnings: List[str] = []

        if requested < now_local:
            requested += timedelta(days=1)
            warnings.append(
                f"Запрошенное время {value} уже прошло сегодня — переношу на {requested.strftime('%d.%m %H:%M')}"
            )

        return requested, warnings

    def _fits_reasonable_window(self, start_time: datetime, duration_hours: float) -> bool:
        start_hour = start_time.hour
        end_time = start_time + timedelta(hours=duration_hours)
        end_hour = end_time.hour

        if start_hour < self.REASONABLE_START_HOURS[0]:
            return False
        if end_hour >= self.REASONABLE_START_HOURS[1]:
            # allow finishing slightly later if within 30 minutes
            if end_time.hour == self.REASONABLE_START_HOURS[1] and end_time.minute <= 30:
                return True
            return False
        return True

    def _suggest_reasonable_time(
        self, current: datetime, duration_hours: float
    ) -> datetime:
        start_hour, end_hour = self.REASONABLE_START_HOURS
        start_of_day = current.replace(hour=start_hour, minute=0, second=0, microsecond=0)

        if current.hour < start_hour:
            return start_of_day

        projected_end = current + timedelta(hours=duration_hours)
        if projected_end.hour < end_hour or (
            projected_end.hour == end_hour and projected_end.minute <= 30
        ):
            return current

        next_day_start = start_of_day + timedelta(days=1)
        return next_day_start


time_scheduler = TimeScheduler()
