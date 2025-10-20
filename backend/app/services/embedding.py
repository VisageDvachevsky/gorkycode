import hashlib
import json
import logging
import os
from typing import List, Optional

import numpy as np
import redis.asyncio as redis

# See services/poi-service/scripts/load_pois.py for context.  The accelerated
# Hugging Face transfer backend occasionally fails inside restricted clusters,
# so we disable it by default for deterministic startup behaviour.
os.environ.setdefault("HF_HUB_DISABLE_HF_TRANSFER", "1")

from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        try:
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        except Exception as exc:  # pragma: no cover - operational safeguard
            cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME") or "~/.cache/sentence-transformers"
            self.logger.error(
                "Failed to load embedding model '%s': %s", settings.EMBEDDING_MODEL, exc
            )
            self.logger.error(
                "Ensure the model weights exist in the container cache (%s) or enable network access.",
                cache_dir,
            )
            raise
        self.redis_client: Optional[redis.Redis] = None
        
    async def connect_redis(self):
        if not self.redis_client:
            self.redis_client = await redis.from_url(settings.REDIS_URL)
    
    def _get_cache_key(self, text: str) -> str:
        return f"embedding:{hashlib.sha256(text.encode()).hexdigest()}"
    
    async def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(text)
        cached = await self.redis_client.get(cache_key)
        
        if cached:
            return json.loads(cached)
        return None
    
    async def cache_embedding(self, text: str, embedding: List[float]) -> None:
        if not self.redis_client:
            await self.connect_redis()
        
        cache_key = self._get_cache_key(text)
        await self.redis_client.set(
            cache_key,
            json.dumps(embedding),
            ex=settings.CACHE_TTL_SECONDS
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    
    async def get_embedding(self, text: str) -> tuple[List[float], bool]:
        cached = await self.get_cached_embedding(text)
        if cached:
            return cached, True
        
        embedding = self.generate_embedding(text)
        await self.cache_embedding(text, embedding)
        return embedding, False
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))


embedding_service = EmbeddingService()