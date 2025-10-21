from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Sequence, Tuple, TypeVar

import grpc

from ai_tourist_common import get_trace_id
from app.core.config import settings
from app.proto import (
    embedding_pb2,
    embedding_pb2_grpc,
    geocoding_pb2,
    geocoding_pb2_grpc,
    llm_pb2,
    llm_pb2_grpc,
    poi_pb2,
    poi_pb2_grpc,
    ranking_pb2,
    ranking_pb2_grpc,
    route_pb2,
    route_pb2_grpc,
)
logger = logging.getLogger(__name__)

TStub = TypeVar("TStub")


class GrpcClient(Generic[TStub], ABC):
    def __init__(self, name: str, url: str) -> None:
        self.name = name
        self.url = url
        self.channel: Optional[grpc.aio.Channel] = None
        self._stub: Optional[TStub] = None

    async def connect(self) -> None:
        if self.channel:
            return
        try:
            self.channel = grpc.aio.insecure_channel(self.url)
            self._stub = self._create_stub(self.channel)
            logger.info("Connected to %s at %s", self.name, self.url)
        except Exception:
            logger.exception("Failed to connect to %s at %s", self.name, self.url)
            self.channel = None
            self._stub = None
            raise

    async def close(self) -> None:
        if self.channel:
            await self.channel.close()
        self.channel = None
        self._stub = None

    def stub(self) -> TStub:
        if not self._stub:
            raise RuntimeError(f"{self.name} gRPC stub is not initialised")
        return self._stub

    def is_ready(self) -> bool:
        return self._stub is not None

    def _metadata(self) -> Sequence[Tuple[str, str]]:
        trace_id = get_trace_id()
        if trace_id and trace_id != "-":
            return (("x-trace-id", trace_id),)
        return ()

    @abstractmethod
    def _create_stub(self, channel: grpc.aio.Channel) -> TStub:
        raise NotImplementedError


class EmbeddingClient(GrpcClient[embedding_pb2_grpc.EmbeddingServiceStub]):
    def __init__(self) -> None:
        super().__init__("Embedding Service", settings.EMBEDDING_SERVICE_URL)

    def _create_stub(self, channel: grpc.aio.Channel) -> embedding_pb2_grpc.EmbeddingServiceStub:
        return embedding_pb2_grpc.EmbeddingServiceStub(channel)

    async def generate_embedding(self, text: str, use_cache: bool = True) -> embedding_pb2.EmbeddingResponse:
        request = embedding_pb2.EmbeddingRequest(text=text, use_cache=use_cache)
        return await self.stub().GenerateEmbedding(request, metadata=self._metadata())


class POIClient(GrpcClient[poi_pb2_grpc.POIServiceStub]):
    def __init__(self) -> None:
        super().__init__("POI Service", settings.POI_SERVICE_URL)

    def _create_stub(self, channel: grpc.aio.Channel) -> poi_pb2_grpc.POIServiceStub:
        return poi_pb2_grpc.POIServiceStub(channel)

    async def get_all_pois(self, categories: Optional[List[str]] = None, with_embeddings: bool = True):
        request = poi_pb2.GetPOIsRequest(categories=categories or [], with_embeddings=with_embeddings)
        response = await self.stub().GetAllPOIs(request, metadata=self._metadata())
        return response.pois

    async def get_categories(self) -> List[Dict[str, int | str]]:
        response = await self.stub().GetCategories(
            poi_pb2.GetCategoriesRequest(), metadata=self._metadata()
        )
        return [
            {"value": category.value, "label": category.label, "count": category.count}
            for category in response.categories
        ]

    async def find_cafes_near_location(self, lat: float, lon: float, radius_km: float = 1.0):
        request = poi_pb2.CafeSearchRequest(lat=lat, lon=lon, radius_km=radius_km)
        response = await self.stub().FindCafesNearLocation(request, metadata=self._metadata())
        return response.cafes


class RankingClient(GrpcClient[ranking_pb2_grpc.RankingServiceStub]):
    def __init__(self) -> None:
        super().__init__("Ranking Service", settings.RANKING_SERVICE_URL)

    def _create_stub(self, channel: grpc.aio.Channel) -> ranking_pb2_grpc.RankingServiceStub:
        return ranking_pb2_grpc.RankingServiceStub(channel)

    async def rank_pois(
        self,
        user_embedding: List[float],
        social_mode: str,
        intensity: str,
        top_k: int = 20,
        categories_filter: Optional[List[str]] = None,
    ):
        request = ranking_pb2.RankingRequest(
            user_embedding=user_embedding,
            social_mode=social_mode,
            intensity=intensity,
            top_k=top_k,
            categories_filter=categories_filter or [],
        )
        response = await self.stub().RankPOIs(request, metadata=self._metadata())
        return response.scored_pois


class RoutePlannerClient(GrpcClient[route_pb2_grpc.RoutePlannerServiceStub]):
    def __init__(self) -> None:
        super().__init__("Route Planner Service", settings.ROUTE_SERVICE_URL)

    def _create_stub(self, channel: grpc.aio.Channel) -> route_pb2_grpc.RoutePlannerServiceStub:
        return route_pb2_grpc.RoutePlannerServiceStub(channel)

    async def optimize_route(
        self,
        start_lat: float,
        start_lon: float,
        pois: List[route_pb2.POIInfo],
        available_hours: float,
        intensity: str,
    ) -> route_pb2.RouteOptimizationResponse:
        request = route_pb2.RouteOptimizationRequest(
            start_lat=start_lat,
            start_lon=start_lon,
            pois=pois,
            available_hours=available_hours,
            intensity=intensity,
        )
        return await self.stub().OptimizeRoute(request, metadata=self._metadata())

    async def calculate_route_geometry(
        self,
        start_lat: float,
        start_lon: float,
        waypoints: Sequence[Tuple[float, float]],
    ) -> route_pb2.RouteGeometryResponse:
        coords = [route_pb2.Coordinate(lat=lat, lon=lon) for lat, lon in waypoints]
        request = route_pb2.RouteGeometryRequest(start_lat=start_lat, start_lon=start_lon, waypoints=coords)
        return await self.stub().CalculateRouteGeometry(request, metadata=self._metadata())


class LLMClient(GrpcClient[llm_pb2_grpc.LLMServiceStub]):
    def __init__(self) -> None:
        super().__init__("LLM Service", settings.LLM_SERVICE_URL)

    def _create_stub(self, channel: grpc.aio.Channel) -> llm_pb2_grpc.LLMServiceStub:
        return llm_pb2_grpc.LLMServiceStub(channel)

    async def generate_route_explanation(self, request: llm_pb2.RouteExplanationRequest) -> llm_pb2.RouteExplanationResponse:
        return await self.stub().GenerateRouteExplanation(request, metadata=self._metadata())


class GeocodingClient(GrpcClient[geocoding_pb2_grpc.GeocodingServiceStub]):
    def __init__(self) -> None:
        super().__init__("Geocoding Service", settings.GEOCODING_SERVICE_URL)

    def _create_stub(self, channel: grpc.aio.Channel) -> geocoding_pb2_grpc.GeocodingServiceStub:
        return geocoding_pb2_grpc.GeocodingServiceStub(channel)

    async def geocode_address(self, address: str, city: str = "Нижний Новгород"):
        request = geocoding_pb2.GeocodeRequest(address=address, city=city)
        return await self.stub().GeocodeAddress(request, metadata=self._metadata())

    async def validate_coordinates(self, lat: float, lon: float):
        request = geocoding_pb2.CoordinateValidationRequest(lat=lat, lon=lon)
        return await self.stub().ValidateCoordinates(request, metadata=self._metadata())


class GRPCClients:
    def __init__(self) -> None:
        self.embedding_client = EmbeddingClient()
        self.poi_client = POIClient()
        self.ranking_client = RankingClient()
        self.route_planner_client = RoutePlannerClient()
        self.llm_client = LLMClient()
        self.geocoding_client = GeocodingClient()
        self._clients: Tuple[GrpcClient[Any], ...] = (
            self.embedding_client,
            self.poi_client,
            self.ranking_client,
            self.route_planner_client,
            self.llm_client,
            self.geocoding_client,
        )

    async def connect_all(self) -> None:
        for client in self._clients:
            await client.connect()

    async def close_all(self) -> None:
        for client in self._clients:
            await client.close()

    async def health_check(self) -> Dict[str, bool]:
        return {client.name.lower().replace(" ", "_"): client.is_ready() for client in self._clients}


grpc_clients = GRPCClients()
