from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


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


class RouteResponse(BaseModel):
    summary: str
    route: List[POIInRoute]
    total_est_minutes: int
    total_distance_km: float
    notes: List[str] = []
    atmospheric_description: Optional[str] = None
    route_geometry: Optional[List[List[float]]] = None


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