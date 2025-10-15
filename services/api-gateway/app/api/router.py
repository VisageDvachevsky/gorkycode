from fastapi import APIRouter

from app.api.endpoints import route

api_router = APIRouter()

api_router.include_router(route.router, prefix="/route", tags=["route"])