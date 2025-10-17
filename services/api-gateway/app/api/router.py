from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

api_router = APIRouter()

try:
    from app.api.endpoints import route, categories, embedding
    api_router.include_router(route.router, prefix="/route", tags=["routes"])
    api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
    api_router.include_router(embedding.router, prefix="/embedding", tags=["embedding"])
    logger.info("All API endpoints loaded")
except ImportError as e:
    logger.error(f"Failed to load endpoints: {e}")
    
    @api_router.get("/status")
    async def status():
        return {"status": "limited", "error": str(e)}
