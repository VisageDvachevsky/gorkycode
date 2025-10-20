import hashlib
import logging
import os
import pickle
from typing import List

import grpc
import redis.asyncio as aioredis

# See services/poi-service/scripts/load_pois.py for context on disabling the
# accelerated HF transfer backend by default.
os.environ.setdefault("HF_HUB_DISABLE_HF_TRANSFER", "1")

from sentence_transformers import SentenceTransformer

from app.proto import embedding_pb2, embedding_pb2_grpc
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServicer(embedding_pb2_grpc.EmbeddingServiceServicer):
    def __init__(self):
        self.model = None
        self.redis_client = None
    
    async def initialize(self):
        """Initialize model and Redis"""
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        try:
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        except Exception as exc:  # pragma: no cover - operational safeguard
            cache_dir = os.getenv("SENTENCE_TRANSFORMERS_HOME") or "~/.cache/sentence-transformers"
            logger.error(
                "Failed to load embedding model '%s': %s", settings.EMBEDDING_MODEL, exc
            )
            logger.error(
                "Ensure the weights are baked into the container (cache dir: %s) or allow outbound network access.",
                cache_dir,
            )
            raise
        logger.info(f"✓ Model loaded (dim={self.model.get_sentence_embedding_dimension()})")
        
        logger.info(f"Connecting to Redis at {settings.REDIS_URL}")
        self.redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=False
        )
        logger.info("✓ Redis connected")
    
    async def GenerateEmbedding(
        self,
        request: embedding_pb2.EmbeddingRequest,
        context
    ) -> embedding_pb2.EmbeddingResponse:
        """Generate embedding for text"""
        try:
            if request.use_cache:
                cached = await self._get_cached_embedding(request.text)
                if cached is not None:
                    return embedding_pb2.EmbeddingResponse(
                        vector=cached,
                        from_cache=True,
                        dimension=len(cached)
                    )
            
            embedding = self.model.encode(
                request.text,
                convert_to_numpy=True,
                show_progress_bar=False
            ).tolist()
            
            if request.use_cache:
                await self._cache_embedding(request.text, embedding)
            
            return embedding_pb2.EmbeddingResponse(
                vector=embedding,
                from_cache=False,
                dimension=len(embedding)
            )
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Embedding generation failed: {str(e)}")
            return embedding_pb2.EmbeddingResponse()
    
    async def BatchEmbedding(
        self,
        request: embedding_pb2.BatchEmbeddingRequest,
        context
    ) -> embedding_pb2.BatchEmbeddingResponse:
        """Generate embeddings for multiple texts"""
        try:
            results = []
            
            for text in request.texts:
                if request.use_cache:
                    cached = await self._get_cached_embedding(text)
                    if cached is not None:
                        results.append(
                            embedding_pb2.EmbeddingVector(
                                vector=cached,
                                from_cache=True
                            )
                        )
                        continue
                
                embedding = self.model.encode(
                    text,
                    convert_to_numpy=True,
                    show_progress_bar=False
                ).tolist()
                
                if request.use_cache:
                    await self._cache_embedding(text, embedding)
                
                results.append(
                    embedding_pb2.EmbeddingVector(
                        vector=embedding,
                        from_cache=False
                    )
                )
            
            return embedding_pb2.BatchEmbeddingResponse(vectors=results)
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Batch embedding failed: {str(e)}")
            return embedding_pb2.BatchEmbeddingResponse()
    
    async def _get_cached_embedding(self, text: str) -> List[float] | None:
        """Get embedding from cache"""
        try:
            cache_key = self._generate_cache_key(text)
            cached = await self.redis_client.get(cache_key)
            
            if cached:
                return pickle.loads(cached)
            
            return None
            
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
            return None
    
    async def _cache_embedding(self, text: str, embedding: List[float]):
        """Cache embedding"""
        try:
            cache_key = self._generate_cache_key(text)
            await self.redis_client.setex(
                cache_key,
                settings.CACHE_TTL_SECONDS,
                pickle.dumps(embedding)
            )
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    def _generate_cache_key(self, text: str) -> str:
        """Generate cache key from text"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{settings.EMBEDDING_MODEL}:{text_hash}"