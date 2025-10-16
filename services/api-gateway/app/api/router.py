from fastapi import APIRouter

from app.api.endpoints import route, categories, embedding

api_router = APIRouter()

api_router.include_router(route.router, prefix="/route", tags=["route"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(embedding.router, prefix="/embedding", tags=["embedding"])
