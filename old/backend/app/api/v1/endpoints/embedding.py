from fastapi import APIRouter

from app.models.schemas import EmbeddingRequest, EmbeddingResponse
from app.services.embedding import embedding_service

router = APIRouter()


@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    embedding, from_cache = await embedding_service.get_embedding(request.text)
    
    return EmbeddingResponse(
        embedding=embedding,
        cache_key="cached" if from_cache else "generated"
    )