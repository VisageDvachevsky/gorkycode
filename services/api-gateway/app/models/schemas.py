from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CoffeePreferences(BaseModel):
    enabled: bool = True
    interval_minutes: int = 90
    preferred_types: List[str] = ["кофейня", "кафе"]


class RouteRequest(BaseModel):
    interests: Optional[str] = None
    hours: float = Field(..., ge=0.5, le=8.0)
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    start_address: Optional[str] = None
    social_mode: Optional[str] = "solo"
    intensity: Optional[str] = "medium"
    categories: Optional[List[str]] = None
    coffee_preferences: Optional[CoffeePreferences] = None
    start_time: Optional[datetime] = None
    client_timezone: Optional[str] = "Europe/Moscow"


class POIInRoute(BaseModel):
    order: int
    poi_id: int
    name: str
    lat: float
    lon: float
    why: str
    tip: str
    est_visit_minutes: int
    arrival_time: datetime
    leave_time: datetime
    is_coffee_break: bool = False


class RouteResponse(BaseModel):
    summary: str
    route: List[POIInRoute]
    total_est_minutes: int
    total_distance_km: float
    notes: List[str]
    atmospheric_description: Optional[str] = None
    route_geometry: List[List[float]] = []
    start_time_used: Optional[datetime] = None
    time_warnings: List[str] = []