import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

api_router = APIRouter()

try:
    from app.api.endpoints import categories, embedding, route

    api_router.include_router(route.router, prefix="/route", tags=["routes"])
    api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
    api_router.include_router(embedding.router, prefix="/embedding", tags=["embedding"])
    logger.info("All API endpoints loaded")
except ImportError as exc:
    logger.error("Failed to load endpoints: %s", exc)

    @api_router.get("/status")
    async def status() -> dict[str, str]:
        return {"status": "limited", "error": str(exc)}

