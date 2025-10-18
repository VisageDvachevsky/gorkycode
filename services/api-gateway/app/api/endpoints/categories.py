from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
import logging

from app.grpc.clients import grpc_clients

logger = logging.getLogger(__name__)
router = APIRouter()


class CategoryResponse(BaseModel):
    value: str
    label: str
    count: int


@router.get("/list", response_model=List[CategoryResponse])
async def get_categories():
    """Get all available POI categories with counts via POI Service"""
    try:
        categories = await grpc_clients.poi_client.get_categories()
        
        response = [
            CategoryResponse(
                value=cat["value"],
                label=cat["label"],
                count=cat["count"]
            )
            for cat in categories
        ]
        
        logger.info(f"Retrieved {len(response)} categories from POI service")
        return response
        
    except Exception as e:
        logger.error(f"Failed to get categories: {e}")
        raise HTTPException(
            status_code=503,
            detail="POI Service unavailable"
        )


@router.get("/popular", response_model=List[CategoryResponse])
async def get_popular_categories(limit: int = 5):
    """Get most popular categories"""
    try:
        all_categories = await get_categories()
        sorted_categories = sorted(all_categories, key=lambda x: x.count, reverse=True)
        return sorted_categories[:limit]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get popular categories: {e}")
        raise HTTPException(
            status_code=503,
            detail="POI Service unavailable"
        )