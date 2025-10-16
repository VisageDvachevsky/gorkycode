from fastapi import APIRouter
from typing import List
from pydantic import BaseModel
import logging

from app.grpc.clients import grpc_clients
from app.grpc.proto import poi_pb2

logger = logging.getLogger(__name__)

router = APIRouter()


class CategoryResponse(BaseModel):
    value: str
    label: str
    count: int


@router.get("/list", response_model=List[CategoryResponse])
async def get_categories():
    """Get all available POI categories with counts"""
    logger.info("Fetching categories from POI service")
    
    response = await grpc_clients.poi.GetCategories(
        poi_pb2.Empty()
    )
    
    categories = [
        CategoryResponse(
            value=cat.value,
            label=cat.label,
            count=cat.count
        )
        for cat in response.categories
    ]
    
    logger.info(f"Retrieved {len(categories)} categories")
    return categories