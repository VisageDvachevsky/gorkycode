import grpc
import logging
from typing import Dict, Optional

from app.proto import (
    embedding_pb2,
    embedding_pb2_grpc,
    ranking_pb2,
    ranking_pb2_grpc,
    route_pb2,
    route_pb2_grpc,
    llm_pb2,
    llm_pb2_grpc,
    geocoding_pb2,
    geocoding_pb2_grpc,
    poi_pb2,
    poi_pb2_grpc,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class GRPCClients:
    def __init__(self):
        self.channels: Dict[str, grpc.aio.Channel] = {}
        self.stubs: Dict[str, any] = {}
    
    async def connect_all(self):
        """Connect to all gRPC services"""
        services = {
            "embedding": (settings.EMBEDDING_SERVICE_URL, embedding_pb2_grpc.EmbeddingServiceStub),
            "ranking": (settings.RANKING_SERVICE_URL, ranking_pb2_grpc.RankingServiceStub),
            "route": (settings.ROUTE_SERVICE_URL, route_pb2_grpc.RoutePlannerServiceStub),
            "llm": (settings.LLM_SERVICE_URL, llm_pb2_grpc.LLMServiceStub),
            "geocoding": (settings.GEOCODING_SERVICE_URL, geocoding_pb2_grpc.GeocodingServiceStub),
            "poi": (settings.POI_SERVICE_URL, poi_pb2_grpc.POIServiceStub),
        }
        
        for service_name, (url, stub_class) in services.items():
            logger.info(f"Connecting to {service_name} service at {url}...")
            
            channel = grpc.aio.insecure_channel(
                url,
                options=[
                    ('grpc.keepalive_time_ms', 30000),
                    ('grpc.keepalive_timeout_ms', 10000),
                    ('grpc.max_receive_message_length', 50 * 1024 * 1024),
                    ('grpc.max_send_message_length', 50 * 1024 * 1024),
                ]
            )
            
            self.channels[service_name] = channel
            self.stubs[service_name] = stub_class(channel)
            
            logger.info(f"✓ Connected to {service_name} service")
    
    async def close_all(self):
        """Close all gRPC connections"""
        for service_name, channel in self.channels.items():
            await channel.close()
            logger.info(f"✓ Closed {service_name} connection")
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services"""
        health_status = {}
        
        for service_name, channel in self.channels.items():
            try:
                await channel.channel_ready()
                health_status[service_name] = True
            except Exception as e:
                logger.error(f"Health check failed for {service_name}: {e}")
                health_status[service_name] = False
        
        return health_status
    
    @property
    def embedding(self) -> embedding_pb2_grpc.EmbeddingServiceStub:
        return self.stubs["embedding"]
    
    @property
    def ranking(self) -> ranking_pb2_grpc.RankingServiceStub:
        return self.stubs["ranking"]
    
    @property
    def route(self) -> route_pb2_grpc.RoutePlannerServiceStub:
        return self.stubs["route"]
    
    @property
    def llm(self) -> llm_pb2_grpc.LLMServiceStub:
        return self.stubs["llm"]
    
    @property
    def geocoding(self) -> geocoding_pb2_grpc.GeocodingServiceStub:
        return self.stubs["geocoding"]
    
    @property
    def poi(self) -> poi_pb2_grpc.POIServiceStub:
        return self.stubs["poi"]


grpc_clients = GRPCClients()