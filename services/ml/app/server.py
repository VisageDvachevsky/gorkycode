import grpc
from concurrent import futures
import logging
import time
import hashlib
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import redis.asyncio as redis

from proto import ml_pb2, ml_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingServicer(ml_pb2_grpc.EmbeddingServiceServicer):
    def __init__(self, model_name: str, redis_url: str):
        logger.info(f"Initializing ML Service with model: {model_name}")
        start = time.time()
        
        self.model = SentenceTransformer(model_name)
        self.model.eval()
        
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.cache_ttl = 86400
        
        elapsed = time.time() - start
        logger.info(f"✓ Model loaded in {elapsed:.2f}s (dimension: {self.model.get_sentence_embedding_dimension()})")
    
    def _cache_key(self, text: str) -> str:
        return f"emb:{hashlib.sha256(text.encode()).hexdigest()}"
    
    async def _get_cached(self, text: str) -> list[float] | None:
        try:
            key = self._cache_key(text)
            cached = await self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
        return None
    
    async def _set_cache(self, text: str, embedding: list[float]):
        try:
            key = self._cache_key(text)
            await self.redis_client.setex(key, self.cache_ttl, json.dumps(embedding))
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    async def GenerateEmbedding(self, request, context):
        start = time.time()
        
        if request.use_cache:
            cached = await self._get_cached(request.text)
            if cached:
                return ml_pb2.EmbeddingResponse(
                    embedding=cached,
                    from_cache=True,
                    dimension=len(cached),
                    latency_ms=(time.time() - start) * 1000
                )
        
        embedding = self.model.encode(request.text, convert_to_tensor=False)
        embedding_list = embedding.tolist()
        
        if request.use_cache:
            await self._set_cache(request.text, embedding_list)
        
        return ml_pb2.EmbeddingResponse(
            embedding=embedding_list,
            from_cache=False,
            dimension=len(embedding_list),
            latency_ms=(time.time() - start) * 1000
        )
    
    async def GenerateEmbeddingBatch(self, request, context):
        start = time.time()
        results = []
        
        for text in request.texts:
            if request.use_cache:
                cached = await self._get_cached(text)
                if cached:
                    results.append(ml_pb2.EmbeddingResult(
                        embedding=cached,
                        from_cache=True
                    ))
                    continue
            
            embedding = self.model.encode(text, convert_to_tensor=False)
            embedding_list = embedding.tolist()
            
            if request.use_cache:
                await self._set_cache(text, embedding_list)
            
            results.append(ml_pb2.EmbeddingResult(
                embedding=embedding_list,
                from_cache=False
            ))
        
        return ml_pb2.EmbeddingBatchResponse(
            results=results,
            total_latency_ms=(time.time() - start) * 1000
        )
    
    def CosineSimilarity(self, request, context):
        v1 = np.array(request.vector1)
        v2 = np.array(request.vector2)
        
        similarity = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
        
        return ml_pb2.SimilarityResponse(similarity=similarity)
    
    async def HealthCheck(self, request, context):
        try:
            cache_size = await self.redis_client.dbsize()
        except:
            cache_size = -1
        
        return ml_pb2.HealthCheckResponse(
            healthy=True,
            model_name=str(self.model),
            model_dimension=self.model.get_sentence_embedding_dimension(),
            cache_size=cache_size
        )


def serve(model_name: str, redis_url: str, port: int = 50051, max_workers: int = 4):
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        options=[
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
        ]
    )
    
    servicer = EmbeddingServicer(model_name, redis_url)
    ml_pb2_grpc.add_EmbeddingServiceServicer_to_server(servicer, server)
    
    server.add_insecure_port(f'[::]:{port}')
    
    logger.info(f"🚀 ML Service listening on port {port}")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    import os
    
    model = os.getenv('MODEL_NAME', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/2')
    port = int(os.getenv('GRPC_PORT', '50051'))
    workers = int(os.getenv('WORKERS', '4'))
    
    serve(model, redis_url, port, workers)