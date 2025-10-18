import grpc
from typing import Optional
from app.grpc.proto import (
    embedding_pb2,
    embedding_pb2_grpc,
    poi_pb2,
    poi_pb2_grpc,
    ranking_pb2,
    ranking_pb2_grpc,
    route_planner_pb2,
    route_planner_pb2_grpc,
    llm_pb2,
    llm_pb2_grpc,
    geocoding_pb2,
    geocoding_pb2_grpc
)


class EmbeddingClient:
    def __init__(self, host: str, port: int):
        self.address = f"{host}:{port}"
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[embedding_pb2_grpc.EmbeddingServiceStub] = None

    async def connect(self):
        self.channel = grpc.aio.insecure_channel(self.address)
        self.stub = embedding_pb2_grpc.EmbeddingServiceStub(self.channel)

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def generate_embedding(self, text: str, use_cache: bool = True):
        request = embedding_pb2.EmbeddingRequest(text=text, use_cache=use_cache)
        response = await self.stub.GenerateEmbedding(request)
        return list(response.vector)


class POIClient:
    def __init__(self, host: str, port: int):
        self.address = f"{host}:{port}"
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[poi_pb2_grpc.POIServiceStub] = None

    async def connect(self):
        self.channel = grpc.aio.insecure_channel(self.address)
        self.stub = poi_pb2_grpc.POIServiceStub(self.channel)

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def search_pois(self, query: str, limit: int = 10):
        request = poi_pb2.SearchRequest(query=query, limit=limit)
        response = await self.stub.SearchPOIs(request)
        return response.pois


class RankingClient:
    def __init__(self, host: str, port: int):
        self.address = f"{host}:{port}"
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[ranking_pb2_grpc.RankingServiceStub] = None

    async def connect(self):
        self.channel = grpc.aio.insecure_channel(self.address)
        self.stub = ranking_pb2_grpc.RankingServiceStub(self.channel)

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def rank_pois(self, user_embedding, poi_ids, preferences):
        request = ranking_pb2.RankingRequest(
            user_embedding=user_embedding,
            poi_ids=poi_ids,
            preferences=preferences
        )
        response = await self.stub.RankPOIs(request)
        return response.ranked_pois


class RoutePlannerClient:
    def __init__(self, host: str, port: int):
        self.address = f"{host}:{port}"
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[route_planner_pb2_grpc.RoutePlannerServiceStub] = None

    async def connect(self):
        self.channel = grpc.aio.insecure_channel(self.address)
        self.stub = route_planner_pb2_grpc.RoutePlannerServiceStub(self.channel)

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def plan_route(self, poi_ids, start_location, preferences):
        request = route_planner_pb2.RouteRequest(
            poi_ids=poi_ids,
            start_location=start_location,
            preferences=preferences
        )
        response = await self.stub.PlanRoute(request)
        return response


class LLMClient:
    def __init__(self, host: str, port: int):
        self.address = f"{host}:{port}"
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[llm_pb2_grpc.LLMServiceStub] = None

    async def connect(self):
        self.channel = grpc.aio.insecure_channel(self.address)
        self.stub = llm_pb2_grpc.LLMServiceStub(self.channel)

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def generate_explanation(self, route, user_preferences):
        request = llm_pb2.ExplanationRequest(
            route=route,
            user_preferences=user_preferences
        )
        response = await self.stub.GenerateExplanation(request)
        return response.explanation


class GeocodingClient:
    def __init__(self, host: str, port: int):
        self.address = f"{host}:{port}"
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[geocoding_pb2_grpc.GeocodingServiceStub] = None

    async def connect(self):
        self.channel = grpc.aio.insecure_channel(self.address)
        self.stub = geocoding_pb2_grpc.GeocodingServiceStub(self.channel)

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def geocode(self, address: str):
        request = geocoding_pb2.GeocodeRequest(address=address)
        response = await self.stub.Geocode(request)
        return response


class GRPCClients:
    def __init__(self):
        self.embedding_client = EmbeddingClient("ai-tourist-embedding-service", 50051)
        self.poi_client = POIClient("ai-tourist-poi-service", 50052)
        self.ranking_client = RankingClient("ai-tourist-ranking-service", 50053)
        self.route_planner_client = RoutePlannerClient("ai-tourist-route-planner-service", 50054)
        self.llm_client = LLMClient("ai-tourist-llm-service", 50055)
        self.geocoding_client = GeocodingClient("ai-tourist-geocoding-service", 50056)

    async def connect_all(self):
        await self.embedding_client.connect()
        await self.poi_client.connect()
        await self.ranking_client.connect()
        await self.route_planner_client.connect()
        await self.llm_client.connect()
        await self.geocoding_client.connect()

    async def close_all(self):
        await self.embedding_client.close()
        await self.poi_client.close()
        await self.ranking_client.close()
        await self.route_planner_client.close()
        await self.llm_client.close()
        await self.geocoding_client.close()


grpc_clients = GRPCClients()