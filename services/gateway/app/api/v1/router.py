from fastapi import APIRouter
from app.api.v1.endpoints import route

api_router = APIRouter()
api_router.include_router(route.router, prefix="/route", tags=["route"])