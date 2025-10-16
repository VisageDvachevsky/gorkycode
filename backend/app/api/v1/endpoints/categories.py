from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel

from app.core.database import get_session
from app.models.poi import POI

router = APIRouter()


class CategoryResponse(BaseModel):
    value: str
    label: str
    count: int 


@router.get("/list", response_model=List[CategoryResponse])
async def get_categories(session: AsyncSession = Depends(get_session)):
    """Get all available POI categories with counts"""
    result = await session.execute(
        select(POI.category, func.count(POI.id).label('count'))
        .group_by(POI.category)
        .order_by(func.count(POI.id).desc())
    )
    
    categories = []
    for row in result:
        categories.append(
            CategoryResponse(
                value=row.category,
                label=row.category.replace('_', ' ').title(),
                count=row.count
            )
        )
    
    return categories