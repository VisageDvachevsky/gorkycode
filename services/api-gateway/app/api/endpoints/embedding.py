from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.grpc.clients import grpc_clients

logger = logging.getLogger(__name__)
router = APIRouter()


class EmbeddingRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=1000)
    use_cache: bool = True


class EmbeddingResponse(BaseModel):
    vector: List[float]
    dimension: int
    from_cache: bool


@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embedding_endpoint(request: EmbeddingRequest) -> EmbeddingResponse:
    try:
        response = await grpc_clients.embedding_client.generate_embedding(
            text=request.text,
            use_cache=request.use_cache,
        )
    except Exception as exc:
        logger.exception("Embedding RPC failed")
        raise HTTPException(503, "Сервис эмбеддингов недоступен") from exc

    vector = list(response.vector)
    if not vector:
        raise HTTPException(503, "Сервис эмбеддингов вернул пустой ответ")

    return EmbeddingResponse(
        vector=vector,
        dimension=response.dimension or len(vector),
        from_cache=response.from_cache,
    )

