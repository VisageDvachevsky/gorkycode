from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

class RouteRequest(BaseModel):
    preferences: List[str]
    duration_hours: float = 2.0
    start_point: Optional[Dict] = None
    intensity: str = "medium"
    social_mode: str = "solo"
    include_coffee: bool = True

class POI(BaseModel):
    id: int
    name: str
    lat: float
    lon: float
    category: str
    visit_duration: int
    description: str

class RouteResponse(BaseModel):
    route: List[POI]
    total_duration: float
    total_distance: float
    explanation: str

@router.post("/plan", response_model=RouteResponse)
async def plan_route(request: RouteRequest):
    """Plan personalized tourist route"""
    
    # Mock response for testing
    mock_route = [
        POI(
            id=1,
            name="Нижегородский Кремль",
            lat=56.328,
            lon=44.002,
            category="fortress",
            visit_duration=60,
            description="Исторический центр города"
        ),
        POI(
            id=2,
            name="Чкаловская лестница",
            lat=56.327,
            lon=43.999,
            category="monument",
            visit_duration=30,
            description="Монументальная лестница с видом на Волгу"
        ),
    ]
    
    return RouteResponse(
        route=mock_route,
        total_duration=request.duration_hours,
        total_distance=3.5,
        explanation="Маршрут составлен с учетом ваших предпочтений"
    )
