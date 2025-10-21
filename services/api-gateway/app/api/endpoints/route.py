from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import RouteRequest, RouteResponse
from app.services import RoutePlanningWorkflow

router = APIRouter()
workflow = RoutePlanningWorkflow()


@router.post("/plan", response_model=RouteResponse)
async def plan_route(request: RouteRequest) -> RouteResponse:
    """HTTP endpoint delegating route planning to the workflow service."""
    return await workflow.plan(request)
