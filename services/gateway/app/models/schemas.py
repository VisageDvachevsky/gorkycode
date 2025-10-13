from datetime import datetime, time as dt_time
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
import pytz


class CoffeePreferences(BaseModel):
    enabled: bool = True
    interval_minutes: int = Field(default=90, ge=30, le=180)
    cuisine: Optional[str] = None
    dietary: Optional[str] = None
    outdoor_seating: bool = False
    wifi: bool = False
    search_radius_km: float = Field(default=0.5, ge=0.1, le=2.0)


class RouteRequest(BaseModel):
    interests: str = Field(default="", description="Free-form text describing interests")
    categories: Optional[List[str]] = Field(default=None, description="Specific POI categories")
    hours: float = Field(..., ge=0.5, le=12, description="Available hours for walk")
    start_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    start_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    start_address: Optional[str] = Field(default=None, description="Starting address")
    social_mode: str = Field(default="solo", pattern="^(solo|friends|family)$")
    coffee_preferences: Optional[CoffeePreferences] = None
    intensity: str = Field(default="medium", pattern="^(relaxed|medium|intense)$")
    allow_transit: bool = Field(default=True, description="Allow public transit suggestions")
    
    # NEW: Time management
    start_time: Optional[str] = Field(
        default=None,
        description="Preferred start time in HH:MM format (client timezone)"
    )
    client_timezone: str = Field(
        default="Europe/Moscow",
        description="Client timezone (IANA format)"
    )
    
    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, "%H:%M")
            except ValueError:
                raise ValueError("start_time must be in HH:MM format")
        return v
    
    @field_validator('client_timezone')
    @classmethod
    def validate_timezone(cls, v):
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {v}")
        return v


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
    is_open: bool = True  # NEW: Is this POI open at arrival time?
    opening_hours: Optional[str] = None  # NEW: Opening hours info


class RouteResponse(BaseModel):
    summary: str
    route: List[POIInRoute]
    total_est_minutes: int
    total_distance_km: float
    notes: List[str] = []
    atmospheric_description: Optional[str] = None
    route_geometry: Optional[List[List[float]]] = None
    start_time_used: datetime  # NEW: Actual start time used
    time_warnings: List[str] = []  # NEW: Warnings about timing


class EmbeddingRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    cache_key: Optional[str] = None


class POIRecommendation(BaseModel):
    poi_id: int
    name: str
    score: float
    reason: str