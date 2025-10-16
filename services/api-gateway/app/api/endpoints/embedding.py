from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import logging

from app.grpc.clients import grpc_clients
from app.grpc.proto import embedding_pb2

logger = logging.getLogger(__name__)

router = APIRouter()


class EmbeddingRequest(BaseModel):
    text: str


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    cache_key: str


@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest) -> EmbeddingResponse:
    """Generate text embedding"""
    logger.info(f"Generating embedding for text: {request.text[:50]}...")
    
    response = await grpc_clients.embedding.GenerateEmbedding(
        embedding_pb2.EmbeddingRequest(
            text=request.text,
            use_cache=True
        )
    )
    
    return EmbeddingResponse(
        embedding=list(response.vector),
        cache_key="cached" if response.from_cache else "generated"
    )
