import grpc
from concurrent import futures
import logging
import os
import json
from typing import Dict, Any

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from celery.result import AsyncResult

from proto import llm_pb2, llm_pb2_grpc
from app.workers.celery_app import celery_app
from app.workers.tasks import generate_route_explanation_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMServicer(llm_pb2_grpc.LLMServiceServicer):
    def __init__(self, provider: str, model: str, api_key: str):
        self.provider = provider
        self.model = model
        
        if provider == "openai":
            self.client = AsyncOpenAI(api_key=api_key)
        elif provider == "anthropic":
            self.client = AsyncAnthropic(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        logger.info(f"✓ LLM Service initialized: {provider}/{model}")
    
    async def GenerateRouteExplanation(self, request, context):
        pois_data = [
            {
                "id": poi.id,
                "name": poi.name,
                "category": poi.category,
                "tags": list(poi.tags),
                "description": poi.description,
                "local_tip": poi.local_tip,
                "rating": poi.rating,
            }
            for poi in request.pois
        ]
        
        result = await self._generate_sync(
            pois_data,
            request.user_interests,
            request.social_mode,
            request.intensity
        )
        
        explanations = [
            llm_pb2.Explanation(
                poi_id=exp["poi_id"],
                why=exp["why"],
                tip=exp.get("tip", "")
            )
            for exp in result["explanations"]
        ]
        
        return llm_pb2.RouteExplanationResponse(
            summary=result["summary"],
            explanations=explanations,
            notes=result.get("notes", []),
            atmospheric_description=result.get("atmospheric_description", ""),
            latency_ms=0
        )
    
    async def GenerateRouteExplanationAsync(self, request, context):
        pois_data = [
            {
                "id": poi.id,
                "name": poi.name,
                "category": poi.category,
                "tags": list(poi.tags),
                "description": poi.description,
                "local_tip": poi.local_tip,
                "rating": poi.rating,
            }
            for poi in request.pois
        ]
        
        task = generate_route_explanation_task.apply_async(
            args=[
                pois_data,
                request.user_interests,
                request.social_mode,
                request.intensity,
                self.provider,
                self.model
            ]
        )
        
        return llm_pb2.TaskResponse(
            task_id=task.id,
            status="PENDING"
        )
    
    async def GetTaskStatus(self, request, context):
        result = AsyncResult(request.task_id, app=celery_app)
        
        if result.ready():
            if result.successful():
                data = result.result
                explanations = [
                    llm_pb2.Explanation(
                        poi_id=exp["poi_id"],
                        why=exp["why"],
                        tip=exp.get("tip", "")
                    )
                    for exp in data["explanations"]
                ]
                
                return llm_pb2.TaskStatusResponse(
                    status="SUCCESS",
                    result=llm_pb2.RouteExplanationResponse(
                        summary=data["summary"],
                        explanations=explanations,
                        notes=data.get("notes", []),
                        atmospheric_description=data.get("atmospheric_description", "")
                    )
                )
            else:
                return llm_pb2.TaskStatusResponse(
                    status="FAILURE",
                    error=str(result.result)
                )
        else:
            return llm_pb2.TaskStatusResponse(status="PENDING")
    
    async def HealthCheck(self, request, context):
        inspector = celery_app.control.inspect()
        active_tasks = inspector.active() or {}
        total_tasks = sum(len(tasks) for tasks in active_tasks.values())
        
        return llm_pb2.HealthCheckResponse(
            healthy=True,
            provider=self.provider,
            model=self.model,
            active_tasks=total_tasks
        )
    
    async def _generate_sync(
        self,
        pois: list[Dict[str, Any]],
        interests: str,
        social_mode: str,
        intensity: str
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(pois, interests, social_mode, intensity)
        
        if self.provider == "anthropic":
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
        else:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4000
            )
            content = response.choices[0].message.content
        
        return self._parse_response(content)
    
    def _build_prompt(self, pois, interests, social_mode, intensity) -> str:
        pois_text = "\n\n".join([
            f"{i+1}. {poi['name']} (ID: {poi['id']})\n"
            f"   Категория: {poi['category']}\n"
            f"   Описание: {poi['description']}\n"
            f"   Теги: {', '.join(poi['tags'])}\n"
            f"   Рейтинг: {poi['rating']}/5.0"
            for i, poi in enumerate(pois)
        ])
        
        return f"""Создай увлекательные объяснения для маршрута.

ПРОФИЛЬ:
- Интересы: {interests or "разнообразные"}
- Формат: {social_mode}
- Темп: {intensity}

ТОЧКИ:
{pois_text}

Верни JSON:
{{
    "summary": "Краткое введение",
    "explanations": [
        {{"poi_id": 1, "why": "Детальное объяснение", "tip": "Совет"}},
        ...
    ],
    "atmospheric_description": "Атмосферное описание",
    "notes": ["Заметка 1", "Заметка 2"]
}}

Только JSON, без markdown."""
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        return json.loads(content)


def serve(provider: str, model: str, api_key: str, port: int = 50052):
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=4))
    
    servicer = LLMServicer(provider, model, api_key)
    llm_pb2_grpc.add_LLMServiceServicer_to_server(servicer, server)
    
    server.add_insecure_port(f'[::]:{port}')
    
    logger.info(f"🚀 LLM Service listening on port {port}")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    provider = os.getenv('LLM_PROVIDER', 'anthropic')
    model = os.getenv('LLM_MODEL', 'claude-sonnet-4-20250514')
    api_key = os.getenv('ANTHROPIC_API_KEY') if provider == 'anthropic' else os.getenv('OPENAI_API_KEY')
    port = int(os.getenv('GRPC_PORT', '50052'))
    
    serve(provider, model, api_key, port)