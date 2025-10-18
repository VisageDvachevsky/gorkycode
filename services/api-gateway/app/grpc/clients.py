import logging
from typing import Dict, Any, List, Optional
import grpc
from grpc import aio

from app.core.config import settings

logger = logging.getLogger(__name__)


class POIGRPCClient:
    """Client for POI Service gRPC"""
    
    def __init__(self):
        self.channel: Optional[aio.Channel] = None
        self.stub = None
    
    async def connect(self):
        """Connect to POI service"""
        try:
            self.channel = aio.insecure_channel(settings.POI_SERVICE_URL)
            
            from app.grpc.proto import poi_pb2, poi_pb2_grpc
            self.stub = poi_pb2_grpc.POIServiceStub(self.channel)
            
            logger.info(f"✓ Connected to POI Service: {settings.POI_SERVICE_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to POI service: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.channel:
            await self.channel.close()
            logger.info("✓ POI Service connection closed")
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Get all POI categories with counts"""
        from app.grpc.proto import poi_pb2
        
        try:
            request = poi_pb2.GetCategoriesRequest()
            response = await self.stub.GetCategories(request)
            
            categories = [
                {
                    "value": cat.value,
                    "label": cat.label,
                    "count": cat.count
                }
                for cat in response.categories
            ]
            
            return categories
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting categories: {e.code()} - {e.details()}")
            raise
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            await self.get_categories()
            return True
        except:
            return False


class EmbeddingGRPCClient:
    """Client for Embedding Service gRPC"""
    
    def __init__(self):
        self.channel: Optional[aio.Channel] = None
        self.stub = None
    
    async def connect(self):
        """Connect to Embedding service"""
        try:
            self.channel = aio.insecure_channel(settings.EMBEDDING_SERVICE_URL)
            
            from app.grpc.proto import embedding_pb2, embedding_pb2_grpc
            self.stub = embedding_pb2_grpc.EmbeddingServiceStub(self.channel)
            
            logger.info(f"✓ Connected to Embedding Service: {settings.EMBEDDING_SERVICE_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Embedding service: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.channel:
            await self.channel.close()
            logger.info("✓ Embedding Service connection closed")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        from app.grpc.proto import embedding_pb2
        
        try:
            request = embedding_pb2.EmbeddingRequest(text=text)
            response = await self.stub.GenerateEmbedding(request)
            return list(response.embedding)
            
        except grpc.RpcError as e:
            logger.error(f"gRPC error generating embedding: {e.code()} - {e.details()}")
            raise
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            await self.generate_embedding("test")
            return True
        except:
            return False


class RankingGRPCClient:
    """Client for Ranking Service gRPC"""
    
    def __init__(self):
        self.channel: Optional[aio.Channel] = None
        self.stub = None
    
    async def connect(self):
        """Connect to Ranking service"""
        try:
            self.channel = aio.insecure_channel(settings.RANKING_SERVICE_URL)
            
            from app.grpc.proto import ranking_pb2, ranking_pb2_grpc
            self.stub = ranking_pb2_grpc.RankingServiceStub(self.channel)
            
            logger.info(f"✓ Connected to Ranking Service: {settings.RANKING_SERVICE_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Ranking service: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.channel:
            await self.channel.close()
            logger.info("✓ Ranking Service connection closed")
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        return self.stub is not None


class RoutePlannerGRPCClient:
    """Client for Route Planner Service gRPC"""
    
    def __init__(self):
        self.channel: Optional[aio.Channel] = None
        self.stub = None
    
    async def connect(self):
        """Connect to Route Planner service"""
        try:
            self.channel = aio.insecure_channel(settings.ROUTE_PLANNER_SERVICE_URL)
            
            from app.grpc.proto import route_pb2, route_pb2_grpc
            self.stub = route_pb2_grpc.RoutePlannerServiceStub(self.channel)
            
            logger.info(f"✓ Connected to Route Planner Service: {settings.ROUTE_PLANNER_SERVICE_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Route Planner service: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.channel:
            await self.channel.close()
            logger.info("✓ Route Planner Service connection closed")
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        return self.stub is not None


class LLMGRPCClient:
    """Client for LLM Service gRPC"""
    
    def __init__(self):
        self.channel: Optional[aio.Channel] = None
        self.stub = None
    
    async def connect(self):
        """Connect to LLM service"""
        try:
            self.channel = aio.insecure_channel(settings.LLM_SERVICE_URL)
            
            from app.grpc.proto import llm_pb2, llm_pb2_grpc
            self.stub = llm_pb2_grpc.LLMServiceStub(self.channel)
            
            logger.info(f"✓ Connected to LLM Service: {settings.LLM_SERVICE_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to LLM service: {e}")
            raise
    
    async def close(self):
        """Close connection"""
        if self.channel:
            await self.channel.close()
            logger.info("✓ LLM Service connection closed")
    
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        return self.stub is not None


class GRPCClients:
    """Manager for all gRPC clients"""
    
    def __init__(self):
        self.poi_client = POIGRPCClient()
        self.embedding_client = EmbeddingGRPCClient()
        self.ranking_client = RankingGRPCClient()
        self.route_planner_client = RoutePlannerGRPCClient()
        self.llm_client = LLMGRPCClient()
    
    async def connect_all(self):
        """Connect to all services"""
        await self.poi_client.connect()
        await self.embedding_client.connect()
        await self.ranking_client.connect()
        await self.route_planner_client.connect()
        await self.llm_client.connect()
        logger.info("✅ All gRPC clients connected")
    
    async def close_all(self):
        """Close all connections"""
        await self.poi_client.close()
        await self.embedding_client.close()
        await self.ranking_client.close()
        await self.route_planner_client.close()
        await self.llm_client.close()
        logger.info("✅ All gRPC clients closed")
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services"""
        return {
            "poi_service": await self.poi_client.health_check(),
            "embedding_service": await self.embedding_client.health_check(),
            "ranking_service": await self.ranking_client.health_check(),
            "route_planner_service": await self.route_planner_client.health_check(),
            "llm_service": await self.llm_client.health_check(),
        }


grpc_clients = GRPCClients()