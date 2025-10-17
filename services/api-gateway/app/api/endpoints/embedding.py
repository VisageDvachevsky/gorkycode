from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class ProfileRequest(BaseModel):
    preferences: List[str]
    intensity: str = "medium"
    social_mode: str = "solo"

@router.post("/profile")
async def create_embedding_profile(request: ProfileRequest):
    """Create user embedding profile"""
    return {
        "profile_id": "mock-profile-123",
        "embedding": [0.1] * 384,  # Mock embedding
        "preferences": request.preferences
    }
