from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from app.models.schemas import RouteRequest, RouteResponse
from app.services.share_store import share_store

from app.domain.route_planning.exceptions import RoutePlanningError
from app.domain.route_planning.service import RoutePlanner

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/plan", response_model=RouteResponse)
async def plan_route(request: RouteRequest) -> RouteResponse:
    planner = RoutePlanner(request)
    try:
        response = await planner.plan()
    except RoutePlanningError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    await share_store.save_route(
        response.share_token,
        response.model_dump(mode="json", exclude_none=True),
    )
    return response


@router.get("/share/{token}", response_model=RouteResponse)
async def load_shared_route(token: str) -> RouteResponse:
    data = await share_store.load_route(token)
    if not data:
        raise HTTPException(404, "Ссылка недействительна или срок хранения истёк")

    try:
        route = RouteResponse.model_validate(data)
    except ValidationError as exc:
        logger.warning("Stored route for %s failed validation: %s", token, exc)
        raise HTTPException(500, "Не удалось восстановить маршрут") from exc

    await share_store.extend_ttl(token)
    return route
