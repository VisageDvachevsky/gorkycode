from fastapi import APIRouter

from app.api.v1.endpoints import embedding, route

api_router = APIRouter()

api_router.include_router(embedding.router, prefix="/embedding", tags=["embedding"])
api_router.include_router(route.router, prefix="/route", tags=["route"])