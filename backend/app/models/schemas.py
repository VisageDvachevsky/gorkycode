from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class RouteRequest(BaseModel):
    interests: str = Field(default="", description="Free-form text: street-art, panoramas, coffee, history")
    categories: Optional[List[str]] = Field(default=None, description="Specific POI categories to include")
    hours: float = Field(..., ge=0.5, le=12, description="Available hours for the walk")
    start_lat: Optional[float] = Field(default=None, ge=-90, le=90)
    start_lon: Optional[float] = Field(default=None, ge=-180, le=180)
    start_address: Optional[str] = Field(default=None, description="Starting address (alternative to coordinates)")
    social_mode: str = Field(default="solo", pattern="^(solo|friends|family)$")
    coffee_preference: Optional[int] = Field(
        default=None, 
        ge=30, 
        le=180, 
        description="Desired coffee break interval in minutes"
    )
    intensity: str = Field(default="medium", pattern="^(relaxed|medium|intense)$")


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