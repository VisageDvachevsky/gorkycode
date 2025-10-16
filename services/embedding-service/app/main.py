import asyncio
import logging
import sys
from concurrent import futures

import grpc
from prometheus_client import start_http_server

from app.proto import embedding_pb2_grpc
from app.services.embedding import EmbeddingServicer
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


async def serve():
    """Start gRPC server"""
    logger.info("🚀 Starting Embedding Service...")
    logger.info(f"Model: {settings.EMBEDDING_MODEL}")
    
    start_http_server(9090)
    logger.info("✓ Prometheus metrics exposed on :9090")
    
    servicer = EmbeddingServicer()
    await servicer.initialize()
    
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
        ]
    )
    
    embedding_pb2_grpc.add_EmbeddingServiceServicer_to_server(servicer, server)
    
    server.add_insecure_port(f'[::]:{settings.GRPC_PORT}')
    
    logger.info(f"✅ Embedding Service listening on port {settings.GRPC_PORT}")
    
    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.run(serve())