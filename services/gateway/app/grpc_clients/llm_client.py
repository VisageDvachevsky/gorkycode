import grpc
import logging
import os
from typing import List, Dict, Any

from app.proto import llm_pb2, llm_pb2_grpc

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.host = os.getenv('LLM_SERVICE_HOST', 'localhost')
        self.port = os.getenv('LLM_SERVICE_PORT', '50052')
        self.channel = None
        self.stub = None
    
    async def connect(self):
        self.channel = grpc.aio.insecure_channel(f'{self.host}:{self.port}')
        self.stub = llm_pb2_grpc.LLMServiceStub(self.channel)
        logger.info(f"✓ LLM client connected to {self.host}:{self.port}")
    
    async def close(self):
        if self.channel:
            await self.channel.close()
    
    async def generate_explanation(
        self,
        pois: List[Dict[str, Any]],
        interests: str,
        social_mode: str,
        intensity: str
    ) -> Dict[str, Any]:
        try:
            poi_messages = [
                llm_pb2.POI(
                    id=poi["id"],
                    name=poi["name"],
                    category=poi.get("category", ""),
                    tags=poi.get("tags", []),
                    description=poi.get("description", ""),
                    local_tip=poi.get("local_tip", ""),
                    rating=poi.get("rating", 0.0)
                )
                for poi in pois
            ]
            
            request = llm_pb2.RouteExplanationRequest(
                pois=poi_messages,
                user_interests=interests,
                social_mode=social_mode,
                intensity=intensity
            )
            
            response = await self.stub.GenerateRouteExplanation(request, timeout=30.0)
            
            return {
                "summary": response.summary,
                "explanations": [
                    {
                        "poi_id": exp.poi_id,
                        "why": exp.why,
                        "tip": exp.tip
                    }
                    for exp in response.explanations
                ],
                "notes": list(response.notes),
                "atmospheric_description": response.atmospheric_description
            }
        
        except grpc.RpcError as e:
            logger.error(f"LLM service error: {e.code()} - {e.details()}")
            raise
    
    async def generate_explanation_async(
        self,
        pois: List[Dict[str, Any]],
        interests: str,
        social_mode: str,
        intensity: str
    ) -> str:
        try:
            poi_messages = [
                llm_pb2.POI(
                    id=poi["id"],
                    name=poi["name"],
                    category=poi.get("category", ""),
                    tags=poi.get("tags", []),
                    description=poi.get("description", ""),
                    local_tip=poi.get("local_tip", ""),
                    rating=poi.get("rating", 0.0)
                )
                for poi in pois
            ]
            
            request = llm_pb2.RouteExplanationRequest(
                pois=poi_messages,
                user_interests=interests,
                social_mode=social_mode,
                intensity=intensity
            )
            
            response = await self.stub.GenerateRouteExplanationAsync(request, timeout=5.0)
            return response.task_id
        
        except grpc.RpcError as e:
            logger.error(f"LLM async error: {e.code()} - {e.details()}")
            raise
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        try:
            request = llm_pb2.TaskStatusRequest(task_id=task_id)
            response = await self.stub.GetTaskStatus(request, timeout=5.0)
            
            if response.status == "SUCCESS":
                result = response.result
                return {
                    "status": "completed",
                    "result": {
                        "summary": result.summary,
                        "explanations": [
                            {
                                "poi_id": exp.poi_id,
                                "why": exp.why,
                                "tip": exp.tip
                            }
                            for exp in result.explanations
                        ],
                        "notes": list(result.notes),
                        "atmospheric_description": result.atmospheric_description
                    }
                }
            elif response.status == "FAILURE":
                return {
                    "status": "failed",
                    "error": response.error
                }
            else:
                return {"status": "pending"}
        
        except grpc.RpcError as e:
            logger.error(f"Task status error: {e.code()} - {e.details()}")
            raise
    
    async def health_check(self) -> bool:
        try:
            request = llm_pb2.HealthCheckRequest()
            response = await self.stub.HealthCheck(request, timeout=5.0)
            return response.healthy
        except:
            return False


llm_client = LLMClient()