from fastapi import APIRouter, HTTPException
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

MOCK_CATEGORIES = [
    {"id": "museums", "name": "Музеи", "count": 15},
    {"id": "parks", "name": "Парки", "count": 12},
    {"id": "churches", "name": "Храмы", "count": 8},
]

@router.get("/")
async def get_categories():
    """Get all available POI categories"""
    return MOCK_CATEGORIES

@router.get("/popular")
async def get_popular_categories(limit: int = 5):
    """Get most popular categories"""
    return MOCK_CATEGORIES[:limit]
