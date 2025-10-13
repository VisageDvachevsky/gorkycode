import grpc
import logging
from typing import List, Tuple
import os

from app.proto import ml_pb2, ml_pb2_grpc

logger = logging.getLogger(__name__)


class MLClient:
    def __init__(self):
        self.host = os.getenv('ML_SERVICE_HOST', 'localhost')
        self.port = os.getenv('ML_SERVICE_PORT', '50051')
        self.channel = None
        self.stub = None
    
    async def connect(self):
        self.channel = grpc.aio.insecure_channel(
            f'{self.host}:{self.port}',
            options=[
                ('grpc.max_send_message_length', 50 * 1024 * 1024),
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),
                ('grpc.keepalive_time_ms', 30000),
                ('grpc.keepalive_timeout_ms', 5000),
                ('grpc.keepalive_permit_without_calls', True),
            ]
        )
        self.stub = ml_pb2_grpc.EmbeddingServiceStub(self.channel)
        logger.info(f"✓ ML client connected to {self.host}:{self.port}")
    
    async def close(self):
        if self.channel:
            await self.channel.close()
    
    async def generate_embedding(
        self, 
        text: str, 
        use_cache: bool = True
    ) -> Tuple[List[float], bool]:
        try:
            request = ml_pb2.EmbeddingRequest(
                text=text,
                use_cache=use_cache
            )
            response = await self.stub.GenerateEmbedding(request, timeout=10.0)
            
            logger.debug(f"Embedding generated: {response.dimension}D, "
                        f"cached={response.from_cache}, "
                        f"latency={response.latency_ms:.2f}ms")
            
            return list(response.embedding), response.from_cache
        except grpc.RpcError as e:
            logger.error(f"ML service error: {e.code()} - {e.details()}")
            raise
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[Tuple[List[float], bool]]:
        try:
            request = ml_pb2.EmbeddingBatchRequest(
                texts=texts,
                use_cache=use_cache
            )
            response = await self.stub.GenerateEmbeddingBatch(request, timeout=30.0)
            
            results = [
                (list(r.embedding), r.from_cache) 
                for r in response.results
            ]
            
            logger.debug(f"Batch generated: {len(results)} embeddings, "
                        f"latency={response.total_latency_ms:.2f}ms")
            
            return results
        except grpc.RpcError as e:
            logger.error(f"ML service batch error: {e.code()} - {e.details()}")
            raise
    
    async def cosine_similarity(
        self,
        vector1: List[float],
        vector2: List[float]
    ) -> float:
        try:
            request = ml_pb2.SimilarityRequest(
                vector1=vector1,
                vector2=vector2
            )
            response = await self.stub.CosineSimilarity(request, timeout=5.0)
            return response.similarity
        except grpc.RpcError as e:
            logger.error(f"Similarity calculation error: {e.code()} - {e.details()}")
            raise
    
    async def health_check(self) -> bool:
        try:
            request = ml_pb2.HealthCheckRequest()
            response = await self.stub.HealthCheck(request, timeout=5.0)
            return response.healthy
        except:
            return False


ml_client = MLClient()