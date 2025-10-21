import logging
from datetime import datetime, time as dt_time, timedelta
from typing import List, Optional, Tuple
import pytz

from app.models.poi import POI

logger = logging.getLogger(__name__)


class TimeScheduler:
    """Smart time management for routes"""
    
    REASONABLE_START_HOURS = (8, 22)  # 8 AM to 10 PM
    DEFAULT_TIMEZONE = "Europe/Moscow"
    
    # City-specific opening hours patterns
    TYPICAL_HOURS = {
        "cafe": (dt_time(8, 0), dt_time(23, 0)),
        "museum": (dt_time(10, 0), dt_time(20, 0)),
        "park": (dt_time(0, 0), dt_time(23, 59)),  # Usually open
        "viewpoint": (dt_time(0, 0), dt_time(23, 59)),  # Always accessible
        "bar": (dt_time(12, 0), dt_time(2, 0)),
        "streetfood": (dt_time(10, 0), dt_time(23, 0)),
        "shopping": (dt_time(10, 0), dt_time(22, 0)),
        "religious_site": (dt_time(7, 0), dt_time(20, 0)),
        "default": (dt_time(9, 0), dt_time(21, 0))
    }
    
    def __init__(self):
        pass
    
    def determine_start_time(
        self,
        requested_time: Optional[str],
        client_timezone_str: str,
        available_hours: float
    ) -> Tuple[datetime, List[str]]:
        """
        Determine optimal start time considering:
        - User's requested time
        - User's timezone
        - Reasonable hours
        - Route duration
        """
        warnings = []
        
        try:
            client_tz = pytz.timezone(client_timezone_str)
        except:
            logger.warning(f"Invalid timezone {client_timezone_str}, using default")
            client_tz = pytz.timezone(self.DEFAULT_TIMEZONE)
            warnings.append(f"⚠️ Неизвестный timezone, используем {self.DEFAULT_TIMEZONE}")
        
        now_client = datetime.now(client_tz)
        
        # If user provided start_time
        if requested_time:
            try:
                hour, minute = map(int, requested_time.split(":"))
                start_dt = now_client.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # If requested time is in the past today, schedule for tomorrow
                if start_dt < now_client:
                    start_dt += timedelta(days=1)
                    warnings.append(f"⏰ Запрошенное время {requested_time} уже прошло сегодня, планируем на завтра")
                
                # Check if reasonable
                if not self._is_reasonable_time(start_dt, available_hours):
                    suggested = self._suggest_reasonable_time(start_dt, available_hours, client_tz)
                    warnings.append(
                        f"⚠️ Запрошенное время {requested_time} неоптимально "
                        f"(маршрут займёт {available_hours}ч). "
                        f"Рекомендуем начать в {suggested.strftime('%H:%M')}"
                    )
                    # But still use requested time
                
                logger.info(f"✓ Using requested start time: {start_dt.strftime('%Y-%m-%d %H:%M %Z')}")
                return start_dt, warnings
                
            except Exception as e:
                logger.error(f"Failed to parse requested_time {requested_time}: {e}")
                warnings.append(f"⚠️ Не удалось разобрать время '{requested_time}', используем текущее")
        
        # No requested time - use current time if reasonable
        current_hour = now_client.hour
        
        if self.REASONABLE_START_HOURS[0] <= current_hour < self.REASONABLE_START_HOURS[1]:
            # Current time is fine
            logger.info(f"✓ Using current time: {now_client.strftime('%Y-%m-%d %H:%M %Z')}")
            return now_client, warnings
        else:
            # Current time is too early or too late
            suggested = self._suggest_reasonable_time(now_client, available_hours, client_tz)
            warnings.append(
                f"⏰ Сейчас {now_client.strftime('%H:%M')}, что неоптимально для прогулки. "
                f"Планируем маршрут на {suggested.strftime('%H:%M')}"
            )
            logger.info(f"✓ Adjusted to reasonable time: {suggested.strftime('%Y-%m-%d %H:%M %Z')}")
            return suggested, warnings
    
    def _is_reasonable_time(self, start_time: datetime, duration_hours: float) -> bool:
        """Check if start time + duration fits in reasonable hours"""
        start_hour = start_time.hour
        end_time = start_time + timedelta(hours=duration_hours)
        end_hour = end_time.hour
        
        if start_hour < self.REASONABLE_START_HOURS[0]:
            return False
        
        if end_hour > self.REASONABLE_START_HOURS[1]:
            return False
        
        return True
    
    def _suggest_reasonable_time(
        self,
        current_time: datetime,
        duration_hours: float,
        tz: pytz.timezone
    ) -> datetime:
        """Suggest next reasonable start time"""
        current_hour = current_time.hour
        
        # Too early - suggest start of day
        if current_hour < self.REASONABLE_START_HOURS[0]:
            suggested = current_time.replace(
                hour=self.REASONABLE_START_HOURS[0],
                minute=0,
                second=0,
                microsecond=0
            )
            return suggested
        
        # Too late - suggest tomorrow morning
        if current_hour >= self.REASONABLE_START_HOURS[1]:
            suggested = (current_time + timedelta(days=1)).replace(
                hour=self.REASONABLE_START_HOURS[0],
                minute=0,
                second=0,
                microsecond=0
            )
            return suggested
        
        # During reasonable hours but close to end
        latest_start = self.REASONABLE_START_HOURS[1] - int(duration_hours)
        if current_hour > latest_start:
            # Suggest tomorrow
            suggested = (current_time + timedelta(days=1)).replace(
                hour=self.REASONABLE_START_HOURS[0],
                minute=0,
                second=0,
                microsecond=0
            )
            return suggested
        
        return current_time
    
    def check_poi_availability(
        self,
        poi: POI,
        arrival_time: datetime
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if POI is open at arrival time
        Returns: (is_open, opening_hours_str)
        """
        # If POI has explicit schedule
        if poi.open_time and poi.close_time:
            arrival_time_only = arrival_time.time()
            
            # Handle closing time after midnight (e.g., bar closes at 2 AM)
            if poi.close_time < poi.open_time:
                # Open across midnight
                is_open = arrival_time_only >= poi.open_time or arrival_time_only <= poi.close_time
            else:
                is_open = poi.open_time <= arrival_time_only <= poi.close_time
            
            hours_str = f"{poi.open_time.strftime('%H:%M')}-{poi.close_time.strftime('%H:%M')}"
            
            return is_open, hours_str
        
        # Use typical hours for category
        typical_open, typical_close = self.TYPICAL_HOURS.get(
            poi.category,
            self.TYPICAL_HOURS["default"]
        )
        
        arrival_time_only = arrival_time.time()
        
        if typical_close < typical_open:
            is_open = arrival_time_only >= typical_open or arrival_time_only <= typical_close
        else:
            is_open = typical_open <= arrival_time_only <= typical_close
        
        hours_str = f"{typical_open.strftime('%H:%M')}-{typical_close.strftime('%H:%M')} (типичное)"
        
        return is_open, hours_str
    
    def validate_cafe_timing(
        self,
        cafe_dict: dict,
        arrival_time: datetime
    ) -> bool:
        """
        Validate if cafe from 2GIS is open at arrival time
        """
        schedule = cafe_dict.get("schedule", {})
        
        if not schedule:
            # Assume typical cafe hours
            arrival_hour = arrival_time.hour
            return 8 <= arrival_hour <= 23
        
        # Parse 2GIS schedule format
        # Example: schedule = {"Mon": "08:00-23:00", ...}
        weekday = arrival_time.strftime("%a")  # Mon, Tue, etc.
        
        if weekday not in schedule:
            return True  # Unknown, assume open
        
        day_schedule = schedule[weekday]
        
        if day_schedule == "Closed" or day_schedule == "closed":
            return False
        
        try:
            open_str, close_str = day_schedule.split("-")
            open_hour, open_min = map(int, open_str.split(":"))
            close_hour, close_min = map(int, close_str.split(":"))
            
            open_time = dt_time(open_hour, open_min)
            close_time = dt_time(close_hour, close_min)
            
            arrival_time_only = arrival_time.time()
            
            if close_time < open_time:
                return arrival_time_only >= open_time or arrival_time_only <= close_time
            else:
                return open_time <= arrival_time_only <= close_time
                
        except:
            return True  # Parsing failed, assume open
    
    def add_time_warnings_to_route(
        self,
        route: List[Tuple[POI, datetime, datetime]],  # (poi, arrival, leave)
    ) -> List[str]:
        """
        Generate time-related warnings for the route
        """
        warnings = []
        
        for poi, arrival, leave in route:
            is_open, hours_str = self.check_poi_availability(poi, arrival)
            
            if not is_open:
                warnings.append(
                    f"⚠️ {poi.name} может быть закрыт в {arrival.strftime('%H:%M')} "
                    f"(обычно работает {hours_str})"
                )
        
        # Check if route ends too late
        last_poi, last_arrival, last_leave = route[-1]
        if last_leave.hour >= 22:
            warnings.append(
                f"🌙 Маршрут заканчивается поздно ({last_leave.strftime('%H:%M')}). "
                f"Учитывайте темноту и транспорт."
            )
        
        return warnings


time_scheduler = TimeScheduler()