import grpc
import logging
from typing import Optional, List, Dict

from app.proto import (
    embedding_pb2,
    embedding_pb2_grpc,
    poi_pb2,
    poi_pb2_grpc,
    ranking_pb2,
    ranking_pb2_grpc,
    route_pb2,
    route_pb2_grpc,
    llm_pb2,
    llm_pb2_grpc,
    geocoding_pb2,
    geocoding_pb2_grpc
)
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self, url: str):
        self.url = url
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[embedding_pb2_grpc.EmbeddingServiceStub] = None

    async def connect(self):
        try:
            self.channel = grpc.aio.insecure_channel(self.url)
            self.stub = embedding_pb2_grpc.EmbeddingServiceStub(self.channel)
            logger.info(f"✓ Connected to Embedding Service: {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Embedding service: {e}")
            raise

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def generate_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        request = embedding_pb2.EmbeddingRequest(text=text, use_cache=use_cache)
        response = await self.stub.GenerateEmbedding(request)
        return list(response.vector)


class POIClient:
    def __init__(self, url: str):
        self.url = url
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[poi_pb2_grpc.POIServiceStub] = None

    async def connect(self):
        try:
            self.channel = grpc.aio.insecure_channel(self.url)
            self.stub = poi_pb2_grpc.POIServiceStub(self.channel)
            logger.info(f"✓ Connected to POI Service: {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to POI service: {e}")
            raise

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def get_all_pois(self, categories: List[str] = None, with_embeddings: bool = True):
        request = poi_pb2.GetPOIsRequest(
            categories=categories or [],
            with_embeddings=with_embeddings
        )
        response = await self.stub.GetAllPOIs(request)
        return response.pois

    async def get_categories(self) -> List[Dict]:
        request = poi_pb2.GetCategoriesRequest()
        response = await self.stub.GetCategories(request)
        
        return [
            {
                "value": cat.value,
                "label": cat.label,
                "count": cat.count
            }
            for cat in response.categories
        ]

    async def find_cafes_near_location(self, lat: float, lon: float, radius_km: float = 1.0):
        request = poi_pb2.CafeSearchRequest(
            lat=lat,
            lon=lon,
            radius_km=radius_km
        )
        response = await self.stub.FindCafesNearLocation(request)
        return response.cafes


class RankingClient:
    def __init__(self, url: str):
        self.url = url
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[ranking_pb2_grpc.RankingServiceStub] = None

    async def connect(self):
        try:
            self.channel = grpc.aio.insecure_channel(self.url)
            self.stub = ranking_pb2_grpc.RankingServiceStub(self.channel)
            logger.info(f"✓ Connected to Ranking Service: {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Ranking service: {e}")
            raise

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def rank_pois(
        self,
        user_embedding: List[float],
        social_mode: str,
        intensity: str,
        top_k: int = 20,
        categories_filter: List[str] = None
    ):
        request = ranking_pb2.RankingRequest(
            user_embedding=user_embedding,
            social_mode=social_mode,
            intensity=intensity,
            top_k=top_k,
            categories_filter=categories_filter or []
        )
        response = await self.stub.RankPOIs(request)
        return response.scored_pois


class RoutePlannerClient:
    def __init__(self, url: str):
        self.url = url
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[route_pb2_grpc.RoutePlannerServiceStub] = None

    async def connect(self):
        try:
            self.channel = grpc.aio.insecure_channel(self.url)
            self.stub = route_pb2_grpc.RoutePlannerServiceStub(self.channel)
            logger.info(f"✓ Connected to Route Planner Service: {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Route Planner service: {e}")
            raise

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def optimize_route(
        self,
        start_lat: float,
        start_lon: float,
        pois: List,
        available_hours: float
    ):
        poi_infos = [
            route_pb2.POIInfo(
                id=poi.poi_id,
                name=poi.name,
                lat=poi.lat,
                lon=poi.lon,
                avg_visit_minutes=poi.avg_visit_minutes,
                rating=poi.rating
            )
            for poi in pois
        ]
        
        request = route_pb2.RouteOptimizationRequest(
            start_lat=start_lat,
            start_lon=start_lon,
            pois=poi_infos,
            available_hours=available_hours
        )
        response = await self.stub.OptimizeRoute(request)
        return response

    async def calculate_route_geometry(
        self,
        start_lat: float,
        start_lon: float,
        waypoints: List[tuple]
    ):
        coords = [
            route_pb2.Coordinate(lat=lat, lon=lon)
            for lat, lon in waypoints
        ]
        
        request = route_pb2.RouteGeometryRequest(
            start_lat=start_lat,
            start_lon=start_lon,
            waypoints=coords
        )
        response = await self.stub.CalculateRouteGeometry(request)
        return response


class LLMClient:
    def __init__(self, url: str):
        self.url = url
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[llm_pb2_grpc.LLMServiceStub] = None

    async def connect(self):
        try:
            self.channel = grpc.aio.insecure_channel(self.url)
            self.stub = llm_pb2_grpc.LLMServiceStub(self.channel)
            logger.info(f"✓ Connected to LLM Service: {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to LLM service: {e}")
            raise

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def generate_route_explanation(
        self,
        route_pois,
        user_interests: str,
        social_mode: str,
        intensity: str
    ):
        poi_contexts = [
            llm_pb2.POIContext(
                id=poi.poi_id,
                name=poi.name,
                description=poi.description,
                category=poi.category,
                tags=list(poi.tags) if hasattr(poi, 'tags') else [],
                local_tip=poi.local_tip if hasattr(poi, 'local_tip') else ""
            )
            for poi in route_pois
        ]
        
        request = llm_pb2.RouteExplanationRequest(
            route=poi_contexts,
            user_interests=user_interests or "",
            social_mode=social_mode,
            intensity=intensity
        )
        response = await self.stub.GenerateRouteExplanation(request)
        return response


class GeocodingClient:
    def __init__(self, url: str):
        self.url = url
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[geocoding_pb2_grpc.GeocodingServiceStub] = None

    async def connect(self):
        try:
            self.channel = grpc.aio.insecure_channel(self.url)
            self.stub = geocoding_pb2_grpc.GeocodingServiceStub(self.channel)
            logger.info(f"✓ Connected to Geocoding Service: {self.url}")
        except Exception as e:
            logger.error(f"Failed to connect to Geocoding service: {e}")
            raise

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def geocode_address(self, address: str, city: str = "Нижний Новгород"):
        request = geocoding_pb2.GeocodeRequest(
            address=address,
            city=city
        )
        response = await self.stub.GeocodeAddress(request)
        return response

    async def validate_coordinates(self, lat: float, lon: float):
        request = geocoding_pb2.CoordinateValidationRequest(
            lat=lat,
            lon=lon
        )
        response = await self.stub.ValidateCoordinates(request)
        return response


class GRPCClients:
    def __init__(self):
        self.embedding_client = EmbeddingClient(settings.EMBEDDING_SERVICE_URL)
        self.poi_client = POIClient(settings.POI_SERVICE_URL)
        self.ranking_client = RankingClient(settings.RANKING_SERVICE_URL)
        self.route_planner_client = RoutePlannerClient(settings.ROUTE_SERVICE_URL)
        self.llm_client = LLMClient(settings.LLM_SERVICE_URL)
        self.geocoding_client = GeocodingClient(settings.GEOCODING_SERVICE_URL)

    async def connect_all(self):
        """Connect to all gRPC services"""
        await self.poi_client.connect()
        await self.embedding_client.connect()
        await self.ranking_client.connect()
        await self.route_planner_client.connect()
        await self.llm_client.connect()
        await self.geocoding_client.connect()

    async def close_all(self):
        """Close all gRPC connections"""
        await self.embedding_client.close()
        await self.poi_client.close()
        await self.ranking_client.close()
        await self.route_planner_client.close()
        await self.llm_client.close()
        await self.geocoding_client.close()

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services"""
        return {
            "embedding": self.embedding_client.stub is not None,
            "poi": self.poi_client.stub is not None,
            "ranking": self.ranking_client.stub is not None,
            "route_planner": self.route_planner_client.stub is not None,
            "llm": self.llm_client.stub is not None,
            "geocoding": self.geocoding_client.stub is not None,
        }


grpc_clients = GRPCClients()