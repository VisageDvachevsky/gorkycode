from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator, model_validator

DEFAULT_TIMEZONE = "Europe/Moscow"


class CoffeePreferences(BaseModel):
    enabled: bool = True
    interval_minutes: int = Field(90, ge=15, le=240)
    search_radius_km: float = Field(0.6, gt=0.1, le=5.0)
    cuisine: Optional[str] = None
    dietary: Optional[str] = None
    outdoor_seating: Optional[bool] = None
    wifi: Optional[bool] = None


class RouteRequest(BaseModel):
    interests: Optional[str] = Field(default=None, max_length=500)
    categories: Optional[List[str]] = None
    hours: float = Field(..., ge=0.5, le=8.0)
    start_lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    start_lon: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    start_address: Optional[str] = Field(default=None, max_length=255)
    social_mode: Literal["solo", "friends", "family", "couple"] = "solo"
    coffee_preferences: Optional[CoffeePreferences] = None
    intensity: Literal["relaxed", "medium", "intense", "low", "high"] = "medium"
    allow_transit: Optional[bool] = True
    start_time: Optional[str] = None
    client_timezone: Optional[str] = DEFAULT_TIMEZONE

    @field_validator("categories", mode="before")
    @classmethod
    def _normalize_categories(cls, value):
        if not value:
            return None
        cleaned = [item for item in value if item]
        return cleaned or None

    @field_validator("start_time")
    @classmethod
    def _validate_time(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise ValueError("start_time must be in HH:MM format") from exc
        return value

    @model_validator(mode="after")
    def _ensure_start_location(self) -> "RouteRequest":
        if self.start_address:
            return self
        if self.start_lat is None or self.start_lon is None:
            raise ValueError("Either start_address or start_lat/start_lon must be provided")
        return self

    def resolved_timezone(self) -> ZoneInfo:
        tz_name = self.client_timezone or DEFAULT_TIMEZONE
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return ZoneInfo(DEFAULT_TIMEZONE)


class POIInRoute(BaseModel):
    order: int
    poi_id: int
    name: str
    lat: float
    lon: float
    why: str
    tip: Optional[str] = None
    est_visit_minutes: int
    arrival_time: datetime
    leave_time: datetime
    is_coffee_break: bool = False
    is_open: Optional[bool] = None
    opening_hours: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    emoji: Optional[str] = None
    distance_from_previous_km: Optional[float] = None


class CoordinatePoint(BaseModel):
    lat: float
    lon: float


class ManeuverInstruction(BaseModel):
    text: str
    street_name: Optional[str] = None
    distance_m: Optional[float] = None
    duration_sec: Optional[float] = None


class TransitStopInfo(BaseModel):
    name: str
    side: Optional[str] = None
    position: Optional[CoordinatePoint] = None


class TransitGuidance(BaseModel):
    provider: Optional[str] = None
    line_name: Optional[str] = None
    vehicle_type: Optional[str] = None
    direction: Optional[str] = None
    vehicle_number: Optional[str] = None
    summary: Optional[str] = None
    boarding: Optional[TransitStopInfo] = None
    alighting: Optional[TransitStopInfo] = None
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None
    notes: Optional[str] = None
    walk_to_board_meters: Optional[float] = None
    walk_from_alight_meters: Optional[float] = None


class RouteLegInstruction(BaseModel):
    mode: Literal["walking", "transit", "mixed"]
    start: CoordinatePoint
    end: CoordinatePoint
    distance_km: float
    duration_minutes: float
    maneuvers: List[ManeuverInstruction] = Field(default_factory=list)
    transit: Optional[TransitGuidance] = None


class RouteResponse(BaseModel):
    summary: str
    route: List[POIInRoute]
    total_est_minutes: int
    total_distance_km: float
    notes: List[str]
    atmospheric_description: Optional[str] = None
    route_geometry: List[List[float]] = Field(default_factory=list)
    start_time_used: Optional[datetime] = None
    time_warnings: List[str] = Field(default_factory=list)
    movement_legs: List[RouteLegInstruction] = Field(default_factory=list)
    walking_distance_km: float = 0.0
    transit_distance_km: float = 0.0
    weather_advice: Optional[str] = None
    share_token: Optional[str] = None
